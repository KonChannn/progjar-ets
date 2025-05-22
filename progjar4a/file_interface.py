import os
import json
import base64
from glob import glob


class FileInterface:
    def __init__(self):
        # Create files directory if it doesn't exist
        if not os.path.exists('files'):
            os.makedirs('files')
        os.chdir('files/')

    def list(self,params=[]):
        try:
            filelist = glob('*.*')
            return dict(status='OK',data=filelist)
        except Exception as e:
            return dict(status='ERROR',data=str(e))

    def get(self,params=[]):
        try:
            filename = params[0]
            if (filename == ''):
                return None
            fp = open(f"{filename}",'rb')
            file_content = fp.read()
            # Convert binary to base64 string for JSON serialization
            file_content_b64 = base64.b64encode(file_content).decode()
            return dict(status='OK',data_namafile=filename,data_file=file_content_b64)
        except Exception as e:
            return dict(status='ERROR',data=str(e))

    def upload(self,params=[]):
        try:
            filename = params[0]
            file_content_b64 = params[1]
            if (filename == '' or file_content_b64 == ''):
                return dict(status='ERROR',data='Invalid parameters')
            
            # Decode base64 content and write to file
            file_content = base64.b64decode(file_content_b64)
            with open(filename, 'wb') as fp:
                fp.write(file_content)
            return dict(status='OK',data=f'File {filename} uploaded successfully')
        except Exception as e:
            return dict(status='ERROR',data=str(e))

    def delete(self,params=[]):
        try:
            filename = params[0]
            if (filename == ''):
                return dict(status='ERROR',data='Invalid filename')
            
            if os.path.exists(filename):
                os.remove(filename)
                return dict(status='OK',data=f'File {filename} deleted successfully')
            else:
                return dict(status='ERROR',data='File not found')
        except Exception as e:
            return dict(status='ERROR',data=str(e))

if __name__=='__main__':
    f = FileInterface()
    print(f.list())
    print(f.get(['pokijan.jpg']))
