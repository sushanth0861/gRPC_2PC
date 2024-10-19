import grpc
from concurrent import futures
import time
import twopc_pb2
import twopc_pb2_grpc
import sqlite3
import logging
import threading
import os

TIMEOUT = 10  # 10 seconds timeout
LOG_FILE = 'coordinator_wal.log'

class TransactionCoordinator(twopc_pb2_grpc.TwoPCServicer):
    def __init__(self, participants, port):
        self.participants = participants
        self.port = port
        self.stubs = [self.create_stub(participant) for participant in participants]
        self.init_db()
        self.lock = threading.Lock()
        self.recover_from_log()

    def create_stub(self, participant):
        channel = grpc.insecure_channel(participant)
        return twopc_pb2_grpc.TwoPCStub(channel)

    def init_db(self):
        self.conn = sqlite3.connect('coordinator.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS transactions
                               (id TEXT PRIMARY KEY, state TEXT, sent_to TEXT)''')
        self.conn.commit()

    def log_state(self, transaction_id, state, sent_to=None):
        with open(LOG_FILE, 'a') as f:
            sent_to_str = "," if sent_to is None else ",".join(map(str, sent_to))
            f.write(f'{transaction_id},{state},{sent_to_str}\n')

    def recover_from_log(self):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    transaction_id = parts[0]
                    state = parts[1]
                    sent_to_str = "," if len(parts) < 3 else parts[2]
                    sent_to = [] if sent_to_str == "," else [int(i) for i in sent_to_str.split(',') if i.isdigit()]
                    self.store_transaction(transaction_id, state, sent_to, log=False)
            os.remove(LOG_FILE)
        self.recover_incomplete_transactions()

    def store_transaction(self, transaction_id, state, sent_to=None, log=True):
        with self.lock:
            if log:
                self.log_state(transaction_id, state, sent_to)
            sent_to_str = "," if sent_to is None else ",".join(map(str, sent_to))
            self.cursor.execute('INSERT OR REPLACE INTO transactions (id, state, sent_to) VALUES (?, ?, ?)',
                                (transaction_id, state, sent_to_str))
            self.conn.commit()

    def get_transaction_state(self, transaction_id):
        with self.lock:
            self.cursor.execute('SELECT state, sent_to FROM transactions WHERE id = ?', (transaction_id,))
            row = self.cursor.fetchone()
            if row:
                state, sent_to_str = row
                sent_to = [] if sent_to_str == "," or sent_to_str == "" else list(map(int, sent_to_str.split(",")))
                return state, sent_to
            return None, []

    def recover_incomplete_transactions(self):
        self.cursor.execute('SELECT id FROM transactions WHERE state = "COMMITTING"')
        transactions = self.cursor.fetchall()
        for transaction_id in transactions:
            self.commit_transaction(transaction_id[0])

    def initialize_transaction(self, transaction_id):
        self.store_transaction(transaction_id, 'INITIALIZED')
        for stub in self.stubs:
            try:
                logging.info(f'Coordinator: Sending Initialize request to participant for transaction {transaction_id}')
                stub.Initialize.future(twopc_pb2.InitializeRequest(transaction_id=transaction_id)).result(timeout=TIMEOUT)
            except grpc.RpcError as e:
                logging.error(f'Error during initialize phase: {e}')
                self.abort_transaction(transaction_id)
                return
            except grpc.FutureTimeoutError:
                logging.error(f'Timeout during initialize phase for transaction {transaction_id}')
                self.abort_transaction(transaction_id)
                return

        self.start_transaction(transaction_id)

    def start_transaction(self, transaction_id):
        state, _ = self.get_transaction_state(transaction_id)
        if state != 'INITIALIZED':
            logging.error(f'Transaction {transaction_id} not initialized properly.')
            return

        self.store_transaction(transaction_id, 'STARTED')
        votes = []
        for stub in self.stubs:
            try:
                logging.info(f'Coordinator: Sending Prepare request to participant for transaction {transaction_id}')
                response = stub.Prepare.future(twopc_pb2.VoteRequest(transaction_id=transaction_id)).result(timeout=TIMEOUT)
                logging.info(f'Coordinator: Received Prepare response from participant for transaction {transaction_id}: {response.vote}')
                votes.append(response.vote)
            except grpc.RpcError as e:
                logging.error(f'Error during prepare phase: {e}')
                self.abort_transaction(transaction_id)
                return
            except grpc.FutureTimeoutError:
                logging.error(f'Timeout during prepare phase for transaction {transaction_id}')
                self.abort_transaction(transaction_id)
                return

        if all(votes):
            self.commit_transaction(transaction_id)
        else:
            logging.info(f'Not all votes are yes, aborting transaction {transaction_id}')
            self.abort_transaction(transaction_id)

    def commit_transaction(self, transaction_id):
        state, sent_to = self.get_transaction_state(transaction_id)

        for i, stub in enumerate(self.stubs):
            if i in sent_to:
                continue
            try:
                logging.info(f'Coordinator: Sending Commit request to participant {i} for transaction {transaction_id}')
                stub.Commit.future(twopc_pb2.CommitRequest(transaction_id=transaction_id)).result(timeout=TIMEOUT)
                sent_to.append(i)
                self.store_transaction(transaction_id, 'COMMITTING', sent_to)
            except grpc.RpcError as e:
                logging.error(f'Error committing transaction {transaction_id} on participant {i}: {e}')
                continue
            except grpc.FutureTimeoutError:
                logging.error(f'Timeout during commit phase for transaction {transaction_id} on participant {i}')
                continue

        if len(sent_to) == len(self.stubs):
            self.store_transaction(transaction_id, 'COMMITTED')
            logging.info(f'Transaction {transaction_id} committed')

    def abort_transaction(self, transaction_id):
        self.store_transaction(transaction_id, 'ABORTING')
        for stub in self.stubs:
            try:
                logging.info(f'Coordinator: Sending Abort request to participant for transaction {transaction_id}')
                stub.Abort.future(twopc_pb2.AbortRequest(transaction_id=transaction_id)).result(timeout=TIMEOUT)
            except grpc.RpcError as e:
                logging.error(f'Error aborting transaction {transaction_id} on a participant: {e}')
            except grpc.FutureTimeoutError:
                logging.error(f'Timeout during abort phase for transaction {transaction_id}')
        self.store_transaction(transaction_id, 'ABORTED')
        logging.info(f'Transaction {transaction_id} aborted')

    def Prepare(self, request, context):
        transaction_id = request.transaction_id
        self.start_transaction(transaction_id)
        return twopc_pb2.VoteResponse(vote=True)

    def Commit(self, request, context):
        transaction_id = request.transaction_id
        self.commit_transaction(transaction_id)
        return twopc_pb2.CommitResponse(success=True)

    def Abort(self, request, context):
        transaction_id = request.transaction_id
        self.abort_transaction(transaction_id)
        return twopc_pb2.AbortResponse(success=True)

    def FetchCommit(self, request, context):
        transaction_id = request.transaction_id
        state, _ = self.get_transaction_state(transaction_id)
        commit = state == 'COMMITTED'
        return twopc_pb2.FetchCommitResponse(commit=commit)

    def serve(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        twopc_pb2_grpc.add_TwoPCServicer_to_server(self, server)
        server.add_insecure_port(f'[::]:{self.port}')
        server.start()
        logging.info(f'Transaction Coordinator started on port {self.port}')
        server.wait_for_termination()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('participants', nargs='+', help='List of participant addresses (e.g., localhost:50051)')
    parser.add_argument('--port', type=int, default=50053, help='Port number for the coordinator')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    coordinator = TransactionCoordinator(args.participants, args.port)
    coordinator.serve()
