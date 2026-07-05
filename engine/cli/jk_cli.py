#!/usr/bin/env python3
import socket
import argparse
import sys
import os

# Add the root directory to sys.path to resolve 'engine' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from engine.security.crypto_utils import encrypt_command, decrypt_response

JK_HOST = "localhost"
JK_PORT = 7474

def send_command(command: str) -> str:
    # In a real setup, we would use SSL/TLS sockets here.
    # For now, we simulate an encrypted channel over standard sockets.
    try:
        with socket.create_connection((JK_HOST, JK_PORT)) as sock:
            encrypted_cmd = encrypt_command(command)
            sock.sendall(encrypted_cmd.encode())
            response = sock.recv(4096).decode()
            return decrypt_response(response)
    except ConnectionRefusedError:
        return "Error: JK is not running (connection refused)."

def main():
    parser = argparse.ArgumentParser(prog='jk')
    parser.add_argument('command', nargs='+', help='Command to execute')
    args = parser.parse_args()
    
    command = ' '.join(args.command)
    print(f"[JK] > {command}")
    result = send_command(command)
    print(f"[JK] < {result}")

if __name__ == "__main__":
    main()
