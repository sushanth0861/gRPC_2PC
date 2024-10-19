import os
import subprocess

def kill_process_on_port(port):
    try:
        # Find the PID of the process using the port
        result = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
        # Extract the PID from the result
        pid = result.strip().split()[-1]
        # Kill the process using the PID
        subprocess.check_output(f'taskkill /PID {pid} /F', shell=True)
        print(f'Process on port {port} (PID {pid}) has been terminated.')
    except subprocess.CalledProcessError as e:
        print(f'No process found running on port {port}.')

if __name__ == '__main__':
    kill_process_on_port(50051)
    kill_process_on_port(50052)
