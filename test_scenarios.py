import time
import logging
import subprocess
import os
import psutil
import grpc
from coordinator import TransactionCoordinator, TIMEOUT
import twopc_pb2
import twopc_pb2_grpc

def kill_process_on_port(port):
    for proc in psutil.process_iter(["pid", "name"]):
        for conn in proc.net_connections(kind="inet"):
            if conn.laddr.port == port:
                proc.kill()
                logging.info(f"Killed process on port {port}")
                return

def restart_coordinator(participants, port):
    command = f'python coordinator.py {" ".join(participants)} --port {port}'
    logging.info(f"Restarting coordinator with command: {command}")
    subprocess.Popen(command, shell=True)
    logging.info("Coordinator restarted")

def test_part1(coordinator, participants, port, transaction_id):
    coordinator.initialize_transaction(transaction_id) 
    logging.info(f"Simulating coordinator failure before sending prepare for transaction {transaction_id}")
    kill_process_on_port(port)  # Kill the coordinator process
    logging.info("Coordinator process killed. Restarting...")
    restart_coordinator(participants, port)  # Restart the coordinator
    logging.info("Coordinator has restarted")
    time.sleep(TIMEOUT + 5)  # Give the coordinator some time to restart
    coordinator.start_transaction(transaction_id)  # Retry the transaction

def test_part2(coordinator, participant_stub, transaction_id):
    coordinator.store_transaction(transaction_id, "STARTED")
    logging.info('Restricting database access for participant to simulate a "no" vote')
    participant_stub.RestrictDBAccess(twopc_pb2.Empty())
    votes = []
    for stub in coordinator.stubs:
        response = stub.Prepare.future(twopc_pb2.VoteRequest(transaction_id=transaction_id)).result(timeout=TIMEOUT)
        votes.append(response.vote)

    logging.info("Allowing database access for participant after the test")
    participant_stub.AllowDBAccess(twopc_pb2.Empty())

    if all(votes):
        coordinator.commit_transaction(transaction_id)
    else:
        coordinator.abort_transaction(transaction_id)

def test_part3(coordinator, participants, port, transaction_id):
    coordinator.store_transaction(transaction_id, "COMMITTING")
    state, sent_to = coordinator.get_transaction_state(transaction_id)

    for i, stub in enumerate(coordinator.stubs):
        if i in sent_to:
            continue  # Skip already sent participants

        try:
            logging.info(f"Sending Commit request to participant {i} for transaction {transaction_id}")
            response = stub.Commit.future(twopc_pb2.CommitRequest(transaction_id=transaction_id)).result(timeout=TIMEOUT)
            logging.info(f"Received Commit response from participant {i} for transaction {transaction_id}")

            sent_to.append(i)
            coordinator.store_transaction(transaction_id, "COMMITTING", sent_to)

            if len(sent_to) == 1:
                logging.info(f"Simulating coordinator failure after sending commit to the first participant for transaction {transaction_id}")
                kill_process_on_port(port)  # Kill the coordinator process
                logging.info("Coordinator process killed. Restarting...")
                time.sleep(TIMEOUT + 5)  # Wait for a while before restarting
                restart_coordinator(participants, port)  # Restart the coordinator
                return  # Exit the function to simulate the failure

        except grpc.RpcError as e:
            logging.error(f"Error committing transaction {transaction_id} on participant {i}: {e}")
            continue
        except grpc.FutureTimeoutError:
            logging.error(f"Timeout during commit phase for transaction {transaction_id} on participant {i}")
            continue

    if len(sent_to) == len(coordinator.stubs):
        coordinator.store_transaction(transaction_id, "COMMITTED")
        logging.info(f"Transaction {transaction_id} committed")

def test_part4(coordinator, transaction_id):
    coordinator.store_transaction(transaction_id, "STARTED")
    for i, stub in enumerate(coordinator.stubs):
        stub.Initialize.future(twopc_pb2.InitializeRequest(transaction_id=transaction_id)).result(timeout=TIMEOUT)
        response = stub.Prepare.future(twopc_pb2.VoteRequest(transaction_id=transaction_id)).result(timeout=TIMEOUT)
        if i == 0:  # Simulate participant failure after voting yes
            logging.info(f"Simulating participant failure after voting yes for transaction {transaction_id}")
            time.sleep(TIMEOUT + 5)  # Simulate participant failure by waiting longer than the timeout
        if response.vote:
            coordinator.store_transaction(transaction_id, "PREPARED")
        else:
            coordinator.abort_transaction(transaction_id)
            return
    coordinator.commit_transaction(transaction_id)

def run_test(coordinator, test_part, participants, port):
    while True:
        transaction_id = input("Enter transaction ID (or 'q' to quit): ")
        if transaction_id.lower() == "q":
            break
        if test_part == 1:
            test_part1(coordinator, participants, port, transaction_id)
        elif test_part == 2:
            participant_stub = twopc_pb2_grpc.TwoPCStub(grpc.insecure_channel(participants[0]))
            test_part2(coordinator, participant_stub, transaction_id)
        elif test_part == 3:
            test_part3(coordinator, participants, port, transaction_id)
        elif test_part == 4:
            test_part4(coordinator, transaction_id)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("participants", nargs="+", help="List of participant addresses (e.g., localhost:50051)")
    parser.add_argument("--test_part", type=int, choices=[1, 2, 3, 4], required=True, help="Which part to test (1, 2, 3, or 4)")
    parser.add_argument("--port", type=int, default=50053, help="Port number for the coordinator")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    coordinator = TransactionCoordinator(args.participants, args.port)
    run_test(coordinator, args.test_part, args.participants, args.port)
