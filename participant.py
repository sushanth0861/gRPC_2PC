import grpc
from concurrent import futures
import time
import threading
import twopc_pb2
import twopc_pb2_grpc
import sqlite3
import logging
import os

TIMEOUT = 10  # 10 seconds timeout
LOG_FILE_TEMPLATE = 'participant_{}_wal.log'

class Participant(twopc_pb2_grpc.TwoPCServicer):
    def __init__(self, node_name, db_name, port):
        self.node_name = node_name
        self.db_name = db_name
        self.port = port
        self.log_file = LOG_FILE_TEMPLATE.format(port)
        self.db_access_restricted = False
        self.init_db()
        self.lock = threading.Lock()
        self.transaction_timeouts = {}
        self.recover_from_log()

    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions
                          (id TEXT PRIMARY KEY, state TEXT)''')
        conn.commit()
        conn.close()

    def log_state(self, transaction_id, state):
        with open(self.log_file, 'a') as f:
            f.write(f'{transaction_id},{state}\n')

    def recover_from_log(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    transaction_id = parts[0]
                    state = parts[1]
                    self.store_transaction(transaction_id, state, log=False)
                    if state == 'PREPARED':
                        self.fetch_commit(transaction_id)
            os.remove(self.log_file)

    def fetch_commit(self, transaction_id):
        coordinator_address = f'localhost:{self.port}'
        channel = grpc.insecure_channel(coordinator_address)
        stub = twopc_pb2_grpc.TwoPCStub(channel)
        logging.info(f'{self.node_name}: Fetching commit information for transaction {transaction_id} from coordinator')
        response = stub.FetchCommit(twopc_pb2.FetchCommitRequest(transaction_id=transaction_id))
        if response.commit:
            self.store_transaction(transaction_id, 'COMMITTED')
            logging.info(f'{self.node_name}: Transaction {transaction_id} committed after recovery')
        else:
            self.store_transaction(transaction_id, 'ABORTED')
            logging.info(f'{self.node_name}: Transaction {transaction_id} aborted after recovery')

    def store_transaction(self, transaction_id, state, log=True):
        with self.lock:
            if log:
                self.log_state(transaction_id, state)
            if self.db_access_restricted:
                logging.warning(f'{self.node_name}: Database access restricted, cannot store transaction {transaction_id}')
                return
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO transactions (id, state) VALUES (?, ?)',
                           (transaction_id, state))
            conn.commit()
            conn.close()

    def get_transaction_state(self, transaction_id):
        with self.lock:
            if self.db_access_restricted:
                logging.warning(f'{self.node_name}: Database access restricted, cannot get transaction state for {transaction_id}')
                return None
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('SELECT state FROM transactions WHERE id = ?', (transaction_id,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None

    def start_transaction_timeout(self, transaction_id):
        def timeout():
            time.sleep(TIMEOUT)
            with self.lock:
                state = self.get_transaction_state(transaction_id)
                if state == 'INITIALIZED':
                    self.store_transaction(transaction_id, 'ABORTED')
                    logging.info(f'{self.node_name}: Aborted transaction {transaction_id} due to timeout')
        thread = threading.Thread(target=timeout)
        thread.start()
        self.transaction_timeouts[transaction_id] = thread

    def Initialize(self, request, context):
        transaction_id = request.transaction_id
        logging.info(f'{self.node_name}: Received Initialize request for transaction {transaction_id}')
        self.store_transaction(transaction_id, 'INITIALIZED')
        self.start_transaction_timeout(transaction_id)
        return twopc_pb2.Empty()

    def Prepare(self, request, context):
        transaction_id = request.transaction_id
        logging.info(f'{self.node_name}: Received Prepare request for transaction {transaction_id}')
        state = self.get_transaction_state(transaction_id)
        if self.db_access_restricted or state != 'INITIALIZED':
            logging.info(f'{self.node_name}: Voting NO due to restricted database access or not initialized for transaction {transaction_id}')
            return twopc_pb2.VoteResponse(vote=False)
        self.store_transaction(transaction_id, 'PREPARED')
        logging.info(f'{self.node_name}: Prepared for transaction {transaction_id}')
        return twopc_pb2.VoteResponse(vote=True)

    def Commit(self, request, context):
        transaction_id = request.transaction_id
        logging.info(f'{self.node_name}: Received Commit request for transaction {transaction_id}')
        self.store_transaction(transaction_id, 'COMMITTED')
        logging.info(f'{self.node_name}: Committed transaction {transaction_id}')
        return twopc_pb2.CommitResponse(success=True)

    def Abort(self, request, context):
        transaction_id = request.transaction_id
        logging.info(f'{self.node_name}: Received Abort request for transaction {transaction_id}')
        self.store_transaction(transaction_id, 'ABORTED')
        logging.info(f'{self.node_name}: Aborted transaction {transaction_id}')
        return twopc_pb2.AbortResponse(success=True)

    def FetchCommit(self, request, context):
        transaction_id = request.transaction_id
        logging.info(f'{self.node_name}: Received FetchCommit request for transaction {transaction_id}')
        state = self.get_transaction_state(transaction_id)
        commit = state == 'COMMITTED'
        logging.info(f'{self.node_name}: FetchCommit response for transaction {transaction_id}: {commit}')
        return twopc_pb2.FetchCommitResponse(commit=commit)

    def RestrictDBAccess(self, request, context):
        self.db_access_restricted = True
        logging.info(f'{self.node_name}: Database access restricted')
        return twopc_pb2.Empty()

    def AllowDBAccess(self, request, context):
        self.db_access_restricted = False
        logging.info(f'{self.node_name}: Database access allowed')
        return twopc_pb2.Empty()

def serve(port, node_name, db_name):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    participant = Participant(node_name, db_name, port)
    twopc_pb2_grpc.add_TwoPCServicer_to_server(participant, server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logging.info(f'{node_name} started on port {port}')
    server.wait_for_termination()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int, help='Port number')
    parser.add_argument('node_name', type=str, help='Name of the participant node')
    parser.add_argument('db_name', type=str, help='Database file name')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    serve(args.port, args.node_name, args.db_name)
