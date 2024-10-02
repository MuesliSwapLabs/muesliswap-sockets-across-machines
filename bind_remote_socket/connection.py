import os
import socket
import threading

from . import VERBOSE_CONNECTION, BLOCK_SIZE

def verbose(s):
    if VERBOSE_CONNECTION:
        print(f" |> {s}")


# Helper function that is used in threads
def relay_connection(source_conn, dest_socket_path):
    """
    Relays communication from a source connection to the destination socket.
    """

    print(f" |> Connection opened by {source_conn}")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as dest_sock:
        with dest_socket_path.get_path() as dest_socket_rpath:
            print(f" |> Connecting to {dest_socket_rpath}")
            verbose(f"Using block size of {BLOCK_SIZE}")
            dest_sock.connect(dest_socket_rpath)
            while True:
                data = source_conn.recv(BLOCK_SIZE)
                if not data:
                    print(f" |> Connection ({dest_socket_rpath}) closed by client")
                    break  # Connection closed by the client
                print(f" |> Sending data to connection ({dest_socket_rpath})")
                verbose(f"Data ({len(data)}b): {data}")
                dest_sock.send(data)
                response = dest_sock.recv(BLOCK_SIZE)
                print(f" |> Receiving response from connection ({dest_socket_rpath})")
                verbose(f"Response ({len(response)}b): {response}")
                source_conn.send(response)



def listen_and_relay(source_socket_path, destination_socket_path):
    """
    Listens for new connections on the source socket and relays communication to the destination socket.
    """
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.bind(source_socket_path.path)
        sock.listen(1)
        print(f" |> Listening for connections on {source_socket_path}")
        while True:
            connection, client_address = sock.accept()
            print(f" |> Accepting connection from {client_address})")
            verbose(f"Connection: {connection}")
            threading.Thread(target=relay_connection, args=(
                connection, destination_socket_path)).start()
