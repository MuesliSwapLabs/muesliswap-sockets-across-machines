#!/usr/bin/env python

import socket
import os
import sys
import threading
import re
from urllib.parse import urlparse
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
from paramiko import SSHClient
import paramiko

BLOCK_SIZE = 1024

class CustomPath:
    def get_path():
        raise NotImplementedError

@dataclass(frozen=True)
class LocalPath(CustomPath):
    path: str

    def get_path():
        return path

@dataclass(frozen=True)
class UrlPath(CustomPath):
    path: str
    hostname: str
    port: int

    def get_path():
        return (hostname, port)

@dataclass(frozen=True)
class SshPath(CustomPath):
    path: str
    hostname: str
    port: int
    user: str

    temp_port = 4041

    @contextmanager
    def get_path():
        try:
            # Create a new socket mapping from the remote host to a local file

            # Open a ssh connection
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.hostname, port=self.port, username=self.username)


            # Run the server side socat command, and ensure it's properly
            # cleaned up when the SSH connection is closed
            cleanup_command = f"""
            nohup bash -c '
            trap "kill 0" EXIT
            sudo socat \"UNIX-CONNECT:{self.path}\" \"TCP-LISTEN:{self.temp_port},fork,reuseaddr\"
            ' &> /dev/null &
            """
            ssh.exec_command(cleanup_command)
            
            yield (hostname, port)
        finally:
            # Close the SSH connection
            ssh.close()
            pass


# Helper function that is used in threads
def relay_connection(source_conn, dest_socket_path):
    """
    Relays communication from a source connection to the destination socket.
    """

    def relay_init():
        pass
    def relay_cleanup():
        pass

    # Init socat if necessary
    if isinstance(source_socket_path, SshPath):
        pass

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as dest_sock:
        with dest_socket_path.get_path() as dest_socket_rpath:
            dest_sock.connect(dest_socket_rpath)
            while True:
                data = source_conn.recv(BLOCK_SIZE)
                if not data:
                    break  # Connection closed by the client
                dest_sock.sendall(data)

    # Cleanup socat if necessary
    if isinstance(source_socket_path, SshPath):
        pass



def listen_and_relay(source_socket_path, destination_socket_path):
    """
    Listens for new connections on the source socket and relays communication to the destination socket.
    """
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.bind(source_socket_path.path)
        sock.listen(1)
        print(f"Listening for connections on {source_socket_path}")
        while True:
            connection, client_address = sock.accept()
            print(f"Received connection from {client_address}")
            threading.Thread(target=relay_connection, args=(
                connection, destination_socket_path)).start()



def parse_url_path_arg(arg):
    # Try to detect an SSH style URL
    pattern = "((?P<username>[^@]*)@)?(?P<hostname>[^:]*)(?P<port>[0-9]{1,7})?:(?P<path>.*)"
    if match := re.match(pattern, arg):
        return SshPath(
                user=match.group("username"),
                hostname=match.group("hostname"),
                path=match.group("path"),
                port=int(match.group("port")) if match.group("port") else 22
            )


    # Try to detect an URL
    url = urlparse(arg)
    if url.netloc and not url.path:
        if not url.scheme:
            url = urlparse(f"http://{arg}")
        return UrlPath(
                hostname=url.hostname,
                port=url.port,
                path=url.path
            )

    # Fallback case: Local path to file
    return LocalPath(path=arg)


if __name__ == "__main__":
    # Define the path for the source and destination socket files
    source_socket_path = parse_url_path_arg(sys.argv[1])
    destination_socket_path = parse_url_path_arg(sys.argv[2])
    print(destination_socket_path)

    if not isinstance(source_socket_path, LocalPath):
        print("Unsupported source file path! Please use a local file path instead")
        exit(1)

    # Ensure the socket file does not already exist
    try:
        os.unlink(source_socket_path.path)
    except OSError:
        if os.path.exists(source_socket_path.path):
            raise

    listen_and_relay(source_socket_path, destination_socket_path)
