from socket import *
import socket
import threading
import logging
import time
import sys
import shlex
import json
import struct
import argparse
from concurrent.futures import ThreadPoolExecutor

from file_protocol import FileProtocol
fp = FileProtocol()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure socket buffer sizes to match client
SOCKET_BUFFER_SIZE = 256 * 1024 * 1024  # 256MB buffer (balanced size)
CHUNK_SIZE = 256 * 1024 * 1024  # 256MB chunks for file transfer

class ProcessTheClient:
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        
        # Optimize socket settings
        self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, struct.pack('i', SOCKET_BUFFER_SIZE))
        self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, struct.pack('i', SOCKET_BUFFER_SIZE))
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # Enable TCP keepalive
        self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Set TCP keepalive parameters
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)

    def receive_all(self, length):
        data = b''
        while len(data) < length:
            packet = self.connection.recv(min(length - len(data), CHUNK_SIZE))
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
    def __init__(self, ipaddress='0.0.0.0', port=8889, max_workers=50):
        self.ipinfo = (ipaddress, port)
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Optimize server socket
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, struct.pack('i', SOCKET_BUFFER_SIZE))
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, struct.pack('i', SOCKET_BUFFER_SIZE))
        self.my_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # Create thread pool with specified number of workers
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.running = True
        logging.info(f"Server initialized with {max_workers} worker threads")
        threading.Thread.__init__(self)

    def stop(self):
        """Stop the server gracefully"""
        self.running = False
        self.my_socket.close()
        self.thread_pool.shutdown(wait=True)

    def run(self):
        logging.warning(f"Thread-based server running on {self.ipinfo}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(100)  # Increased backlog for better concurrency
        
        try:
            while self.running:
                try:
                    self.connection, self.client_address = self.my_socket.accept()
                    logging.warning(f"Connection from {self.client_address}")

                    # Create client handler and submit to thread pool
                    client_handler = ProcessTheClient(self.connection, self.client_address)
                    self.thread_pool.submit(client_handler.handle_client)
                except socket.error:
                    if self.running:
                        raise
                    break
                
        except KeyboardInterrupt:
            logging.info("Shutting down server...")
        except Exception as e:
            logging.error(f"Server error: {str(e)}")
        finally:
            self.stop()

def main():
    parser = argparse.ArgumentParser(description='Thread-based file server with configurable worker count')
    parser.add_argument('--workers', type=int, default=50, help='Number of worker threads (default: 50)')
    parser.add_argument('--port', type=int, default=8889, help='Port to listen on (default: 8889)')
    args = parser.parse_args()

    # Validate worker count
    if args.workers not in [1, 5, 50]:
        logging.error("Worker count must be 1, 5, or 50")
        sys.exit(1)

    svr = Server(ipaddress='0.0.0.0', port=args.port, max_workers=args.workers)
    svr.start()

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down server...")
        svr.stop()
        svr.join()

if __name__ == "__main__":
    main() 