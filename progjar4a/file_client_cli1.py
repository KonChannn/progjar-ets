import socket
import json
import base64
import logging
import time
import struct

server_address=('0.0.0.0',7777)

def send_command(command_str="", binary_data=None):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    logging.warning(f"connecting to {server_address}")
    try:
        # Send command length first (4 bytes)
        command_bytes = command_str.encode()
        command_length = len(command_bytes)
        sock.sendall(struct.pack('!I', command_length))
        
        # Send command
        sock.sendall(command_bytes)
        
        # If there's binary data to send
        if binary_data:
            # Send binary data length
            data_length = len(binary_data)
            sock.sendall(struct.pack('!I', data_length))
            # Send binary data
            sock.sendall(binary_data)
            
        # Look for the response
        data_received = ""
        while True:
            data = sock.recv(1024)
            if data:
                data_received += data.decode()
                if "\r\n\r\n" in data_received:
                    break
            else:
                break
                
        hasil = json.loads(data_received)
        logging.warning("data received from server:")
        return hasil
    except Exception as e:
        logging.warning(f"error during data receiving: {str(e)}")
        return False


def remote_list():
    command_str = "LIST"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        print("daftar file : ")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        print("Gagal")
        return False

def remote_get(filename=""):
    command_str = f"GET {filename}"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        namafile = hasil['data_namafile']
        # Decode base64 string back to binary
        print(hasil['data_file'])
        isifile = base64.b64decode(hasil['data_file'])
        fp = open(namafile,'wb+')
        fp.write(isifile)
        fp.close()
        return True
    else:
        print("Gagal")
        return False

def remote_upload(filename=""):
    try:
        # Read file content in binary mode and encode to base64
        with open(filename, 'rb') as fp:
            file_content = fp.read()
            file_content_b64 = base64.b64encode(file_content).decode()
        
        # Convert base64 string back to binary for sending
        binary_data = file_content_b64.encode()

        print(binary_data)
        
        # Send command and binary data
        command_str = f"UPLOAD {filename}"
        hasil = send_command(command_str, binary_data)
        if (hasil['status']=='OK'):
            print(f"File {filename} berhasil diupload")
            return True
        else:
            print(f"Gagal upload: {hasil['data']}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def remote_delete(filename=""):
    command_str = f"DELETE {filename}"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        print(f"File {filename} berhasil dihapus")
        return True
    else:
        print(f"Gagal menghapus: {hasil['data']}")
        return False

if __name__=='__main__':
    server_address=('172.16.16.101',8889)
    remote_list()
    remote_upload('test.txt')
    remote_list()