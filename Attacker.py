import socket
import random

BROADCAST_PORT = 50000

def receive_shares():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('', BROADCAST_PORT))
        sock.settimeout(3)
        try:
            data, _ = sock.recvfrom(1024)
            return data.decode()
        except socket.timeout:
            return None

def main():
    while True:
        received_share = receive_shares()
        if received_share:
            print(f"Intercepted Share: {received_share}")

if __name__ == "__main__":
    main()
