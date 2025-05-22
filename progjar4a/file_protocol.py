import json
import logging
import shlex
import os

from file_interface import FileInterface

"""
* class FileProtocol bertugas untuk memproses 
data yang masuk, dan menerjemahkannya apakah sesuai dengan
protokol/aturan yang dibuat

* data yang masuk dari client adalah dalam bentuk bytes yang 
pada akhirnya akan diproses dalam bentuk string

* class FileProtocol akan memproses data yang masuk dalam bentuk
string
"""



class FileProtocol:
    def __init__(self):
        self.file = FileInterface()
        # Generate test files if they don't exist
        self.generate_test_files()

    

    def proses_string(self, command='', filename='', content=None):
        logging.warning(f"command: {command}")
        logging.warning(f"filename: {filename}")
        
        try:
            # Convert command to lowercase and strip whitespace
            command = command.lower().strip()
            
            # Handle different commands
            if command == 'list':
                return self.file.list()
            elif command == 'get':
                if not filename:
                    return dict(status='ERROR', data='Filename required for GET command')
                return self.file.get([filename])
            elif command == 'upload':
                if not filename:
                    return dict(status='ERROR', data='Filename required for UPLOAD command')
                if content is None:
                    return dict(status='ERROR', data='Content required for UPLOAD command')
                return self.file.upload([filename, content])
            elif command == 'delete':
                if not filename:
                    return dict(status='ERROR', data='Filename required for DELETE command')
                return self.file.delete([filename])
            elif command == 'generate_test_file':
                if not filename:
                    return dict(status='ERROR', data='Filename required for GENERATE_TEST_FILE command')
                try:
                    size_mb = int(content) if content else 1  # Default to 1MB if no size specified
                    return self.generate_test_file(size_mb, filename)
                except ValueError:
                    return dict(status='ERROR', data='Invalid file size specified')
            else:
                return dict(status='ERROR', data='Unknown command')
                
        except Exception as e:
            return dict(status='ERROR', data=str(e))


if __name__=='__main__':
    #contoh pemakaian
    fp = FileProtocol()
    print(fp.proses_string("LIST"))
    print(fp.proses_string("GET", "pokijan.jpg"))
