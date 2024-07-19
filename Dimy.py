import hashlib
import secrets
import time
import socket
import random
from secretsharing import SecretSharer
from pybloomfilter import BloomFilter

BROADCAST_IP = '255.255.255.255'
BROADCAST_PORT = 50000
BACKEND_SERVER_IP = '127.0.0.1'
BACKEND_SERVER_PORT = 55000

cbf_storage = []

# 32 Byte Ephemeral ID generated on nodes
def generate_ephid():
    return secrets.token_bytes(32)

# Use the Shamir Secret Sharing Mechanism with k = 3 and n = 5 
def create_shares(ephid, k=3, n=5):
    hex_ephid = ephid.hex()
    shares = SecretSharer.split_secret(hex_ephid, k, n)
    return shares

# Broadcast share using UDP
def broadcast_share(share):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(share.encode(), (BROADCAST_IP, BROADCAST_PORT))

# Each Node can receive these shares
def receive_shares():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('', BROADCAST_PORT))
        sock.settimeout(3)
        try:
            data, _ = sock.recvfrom(1024)
            return data.decode()
        except socket.timeout:
            return None

# If 3 out of 5 shares are received then we try to recover the Ephemeral ID.
def reconstruct_ephid(shares):
    try:
        return SecretSharer.recover_secret(shares)
    except:
        return None

# In case of successful Ephemeral ID regernation by a node, that node will generate an Encounter ID.
def generate_encid(ephid):
    private_key = secrets.token_bytes(32)
    public_key = hashlib.sha256(private_key).hexdigest()
    shared_secret = hashlib.sha256(ephid.encode()).hexdigest()
    encid = hashlib.sha256((public_key + shared_secret).encode()).hexdigest()
    return encid

# Create a bloom filter
def create_bloom_filter():
    return BloomFilter(100000, 0.01)

def combine_all_dbfs(dbfs):
    qbf = create_bloom_filter()
    for dbf in dbfs:
        qbf.update(dbf)
    return qbf

def upload_qbf_to_backend(qbf):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((BACKEND_SERVER_IP, BACKEND_SERVER_PORT))
            sock.send(qbf.to_base64().encode())
            result = sock.recv(1024).decode()
            print(f"Received result from server: {result}")
            return result
    except Exception as e:
        print(f"Error sending QBF to server: {e}")
        return None

def upload_cbf_to_backend(cbf):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((BACKEND_SERVER_IP, BACKEND_SERVER_PORT))
            sock.send(cbf.to_base64().encode())
            result = sock.recv(1024).decode()
            print(f"Received upload confirmation from server: {result}")
            return result
    except Exception as e:
        print(f"Error uploading CBF to server: {e}")
        return None

def main():
    start_time = time.time()
    dbf_list = []
    ephid_shares_received = {}

    while True:
        ephid = generate_ephid()
        print(f"Generated EphID: {ephid.hex()}")

        shares = create_shares(ephid)
        for i, share in enumerate(shares):
            # Message Drop Mechanism
            if random.random() >= 0.5:
                print(f"Broadcasting Share {i+1}: {share}")
                broadcast_share(share)
            else:
                print(f"Dropped Share {i+1}")
            time.sleep(3)
        
        for _ in range(len(shares)):
            received_share = receive_shares()
            if received_share:
                ephid_shares_received[received_share] = ephid_shares_received.get(received_share, 0) + 1

        valid_shares = [share for share, count in ephid_shares_received.items() if count >= 3]
        if len(valid_shares) >= 3:
            reconstructed_ephid = reconstruct_ephid(valid_shares[:3])
            if reconstructed_ephid:
                print(f"Reconstructed EphID: {reconstructed_ephid}")
                encid = generate_encid(reconstructed_ephid)
                print(f"Generated EncID: {encid}")

                dbf = create_bloom_filter()
                dbf.add(encid)
                dbf_list.append(dbf)
                print(f"DBF updated with EncID")
        
         # Combine DBFs into QBF every 9 minutes
        if time.time() - start_time >= 9 * 60:
            qbf = combine_all_dbfs(dbf_list)
            print(f"Combined QBF: {qbf}")
            upload_qbf_to_backend(qbf)

            # Reset the timer and clear the dbf_list
            start_time = time.time()
            dbf_list.clear()

        if len(dbf_list) > 6:
            dbf_list.pop(0)

        time.sleep(15 - 3 * len(shares))

if __name__ == "__main__":
    main()

