import os
import socket
import threading

BLOCK_SIZE = 1024

def get_default_ssh_key_path():
    home = os.path.expanduser("~")
    ssh_dir = os.path.join(home, ".ssh")
    
    default_keys = ["id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"]
    
    for key in default_keys:
        key_path = os.path.join(ssh_dir, key)
        if os.path.isfile(key_path):
            return key_path
    
    return None

# Helper function that is used in threads
def relay_connection(source_conn, dest_socket_path):
    """
    Relays communication from a source connection to the destination socket.
    """

    print(f" |> Connection opened by {source_conn}")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as dest_sock:
        with dest_socket_path.get_path() as dest_socket_rpath:
            print(f" |> Connecting to {dest_socket_rpath}")
            dest_sock.connect(dest_socket_rpath)
            while True:
                data = source_conn.recv(BLOCK_SIZE)
                if not data:
                    print(f" |> Connection ({dest_socket_rpath}) closed by client")
                    break  # Connection closed by the client
                print(f" |> Connection ({dest_socket_rpath}) sending data")
                dest_sock.sendall(data)



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
            threading.Thread(target=relay_connection, args=(
                connection, destination_socket_path)).start()

def wrap_terminate_on_exit(command):
    return f"""nohup bash -c '
        trap "kill 0" EXIT
        {command}
        ' &> /dev/null &
        """
