## Instructions to Compile and Run the Programs
### Step 0: Install Required Packages
Before running the programs, you need to install the necessary packages. You can do this using `pip`. Run the following command:

```bash
pip install grpcio grpcio-tools psutil
```
### Step 1: Compile the gRPC Proto File
Before running the programs, you need to compile the twopc.proto file to generate the gRPC Python files.

Run the following command:

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. twopc.proto
```
### Step 2: Start Participant Nodes

Start the participant nodes by running the following commands in separate terminal windows:

```bash
python participant.py 50051 "Participant 1" "participant1.db"
```
```bash
python participant.py 50052 "Participant 2" "participant2.db"
```
### Step 3: Start the Coordinator Node
Start the coordinator node by running the following command:
```bash
python coordinator.py localhost:50051 localhost:50052 --port 50053
```
### Step 4: Run Test Scenarios
To test the different parts of the 2PC protocol, you can use the test_scenarios.py script. For example, to run test part 3, use the following command:

```bash
python test_scenarios.py localhost:50051 localhost:50052 --test_part 3 --port 50053
```
### Step 5: Managing Processes
If you need to kill the coordinator process manually, you can use the following commands to find the process ID (PID) and kill the process:

Find the PID:

```bash
netstat -ano | findstr :50053
```

Kill the process:

```bash
taskkill /PID <PID> /F
```
Replace <PID> with the actual process ID obtained from the previous command.

### Step 6: Clean Up Generated Files
To clean up the generated files (log files, database files, and gRPC Python files), you can use the clean.py script. Run the following command:

```bash
python clean.py
```