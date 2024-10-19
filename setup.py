import subprocess
import sys
import time
import pathlib
import logging

def run_command(command):
    """Run a command and print its output."""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"Command failed with error: {stderr.decode()}")
    else:
        print(stdout.decode())

def main():
    print("Setting up the project...")

    # Step 1: Generate gRPC Python files from the .proto file
    print("Generating gRPC Python files...")
    proto_command = "python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. twopc.proto"
    run_command(proto_command)

    # Check if .proto files were generated successfully
    if not (pathlib.Path('twopc_pb2.py').exists() and pathlib.Path('twopc_pb2_grpc.py').exists()):
        print("Failed to generate gRPC Python files.")
        sys.exit(1)

    # Step 2: Start participant nodes
    print("Starting participant nodes...")

    # Start Participant 1
    p1 = subprocess.Popen(["python", "participant.py", "50051", "Participant 1", "participant1.db"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    time.sleep(1)  # Add a small delay to ensure Participant 1 starts before Participant 2

    # Start Participant 2
    p2 = subprocess.Popen(["python", "participant.py", "50052", "Participant 2", "participant2.db"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    # Print logs from participant nodes
    print("Participant 1 logs:")
    for line in iter(p1.stdout.readline, b''):
        sys.stdout.write(line.decode())
    for line in iter(p1.stderr.readline, b''):
        sys.stderr.write(line.decode())

    print("Participant 2 logs:")
    for line in iter(p2.stdout.readline, b''):
        sys.stdout.write(line.decode())
    for line in iter(p2.stderr.readline, b''):
        sys.stderr.write(line.decode())

    print("Setup complete.")
    print("To run a test scenario, use: python test_scenarios.py localhost:50051 localhost:50052 --test_part [1-4]")

if __name__ == "__main__":
    logging.basicConfig(filename='setup.log', level=logging.DEBUG, format='%(asctime)s %(message)s')
    logger = logging.getLogger()
    main()
