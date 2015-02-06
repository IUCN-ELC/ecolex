import socket


def get_text_tika(file_path):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1',1234))
    f = open(file_path, 'rb')

    while True:
        chunk = f.read(65536)
        if not chunk:
            break
        s.sendall(chunk)

    s.shutdown(socket.SHUT_WR)

    file_content = ''
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        file_content += chunk.decode('utf-8')

    return file_content
