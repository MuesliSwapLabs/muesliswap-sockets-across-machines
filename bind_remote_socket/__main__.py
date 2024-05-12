import os
import sys

from . import listen_and_relay
from .utils import parse_url_path_arg
from .types import LocalPath


if __name__ == "__main__":
    # Define the path for the source and destination socket files
    print(" |> Parsing source arg...")
    source_socket_path = parse_url_path_arg(sys.argv[1])
    print(source_socket_path)
    print(" |> Parsing dest arg...")
    destination_socket_path = parse_url_path_arg(sys.argv[2])
    print(destination_socket_path)

    if not isinstance(source_socket_path, LocalPath):
        print("Unsupported source file path! Please use a local file path instead")
        exit(1)

    # Ensure the socket file does not already exist
    print(" |> Ensuring socket file does not exist...")
    try:
        os.unlink(source_socket_path.path)
    except OSError:
        if os.path.exists(source_socket_path.path):
            raise

    print(" |> Starting listen and relay instance...")
    listen_and_relay(source_socket_path, destination_socket_path)
