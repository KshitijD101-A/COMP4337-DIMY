import socket
import threading
from pybloomfilter import BloomFilter

BACKEND_SERVER_IP = '127.0.0.1'
BACKEND_SERVER_PORT = 55000

cbf_storage = []


def handle_client(client_socket):
    qbf_data = client_socket.recv(1024).decode()
    qbf = BloomFilter.from_base64(qbf_data)

    matched = any(cbf.intersection(qbf) for cbf in cbf_storage)
    result = 'matched' if matched else 'not matched'
    client_socket.send(result.encode())
    client_socket.close()

def server_loop():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((BACKEND_SERVER_IP, BACKEND_SERVER_PORT))
    server.listen(5)
    print(f"[*] Listening on {BACKEND_SERVER_IP}:{BACKEND_SERVER_PORT}")

    while True:
        client_socket, _ = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()

def upload_cbf(cbf):
    cbf_storage.append(cbf)

if __name__ == "__main__":
    server_loop()
