from socket import *
import socket
import threading
import logging
import time
import sys
import shlex
import json
import struct
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

from file_protocol import FileProtocol
fp = FileProtocol()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ProcessTheClient:
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address

    def receive_all(self, length):
        data = b''
        while len(data) < length:
            packet = self.connection.recv(min(length - len(data), 4096))
            if not packet:
                return None
            data += packet
        return data

    def handle_client(self):
        while True:
            try:
                # First receive the command string length (4 bytes)
                length_data = self.connection.recv(4)
                if not length_data:
                    break
                    
                # Unpack the length (network byte order)
                command_length = struct.unpack('!I', length_data)[0]
                
                # Receive the command string
                command_data = self.receive_all(command_length)
                if not command_data:
                    break
                    
                command_str = command_data.decode()
                parts = shlex.split(command_str)
                
                if not parts:
                    continue
                    
                command = parts[0]
                filename = parts[1] if len(parts) > 1 else ''
                
                # If it's an upload command, receive the file data
                content = None
                if command.lower() == 'upload':
                    # Receive file data length
                    length_data = self.connection.recv(4)
                    if length_data:
                        file_length = struct.unpack('!I', length_data)[0]
                        content = self.receive_all(file_length)
                
                hasil = fp.proses_string(command, filename, content)
                hasil = json.dumps(hasil) + "\r\n\r\n"
                self.connection.sendall(hasil.encode())
                
            except Exception as e:
                logging.error(f"Error processing client request: {str(e)}")
                break
                
        self.connection.close()

class Server(threading.Thread):
    def __init__(self, ipaddress='0.0.0.0', port=8889):
        self.ipinfo = (ipaddress, port)
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Create process pool with 50 workers
        self.process_pool = ProcessPoolExecutor(max_workers=50)
        threading.Thread.__init__(self)

    def run(self):
        logging.warning(f"Process-based server running on {self.ipinfo}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(100)  # Increased backlog for better concurrency
        try:
            while True:
                self.connection, self.client_address = self.my_socket.accept()
                logging.warning(f"Connection from {self.client_address}")

                # Create client handler and submit to process pool
                client_handler = ProcessTheClient(self.connection, self.client_address)
                self.process_pool.submit(client_handler.handle_client)
                
        except KeyboardInterrupt:
            logging.info("Shutting down server...")
        finally:
            self.process_pool.shutdown(wait=True)
            self.my_socket.close()

def main():
    svr = Server(ipaddress='0.0.0.0', port=8889)
    svr.start()

if __name__ == "__main__":
    main() 