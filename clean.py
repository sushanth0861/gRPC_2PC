import os
import glob

def cleanup_files():
    files = glob.glob('*.log') + glob.glob('*.db') + glob.glob('*_pb2.py') + glob.glob('*_pb2_grpc.py')
    for file in files:
        try:
            os.remove(file)
            print(f'Removed {file}')
        except Exception as e:
            print(f'Error removing {file}: {e}')

if __name__ == '__main__':
    cleanup_files()
