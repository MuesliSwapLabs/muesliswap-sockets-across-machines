import os
import sys
import re
import getpass
from urllib.parse import urlparse
from paramiko import RSAKey

from .types import LocalPath, SshPath, UrlPath
from .connection import listen_and_relay

from . import VERBOSE_MAIN


def verbose(s):
    if VERBOSE_MAIN:
        print(f" |> {s}")


def get_default_ssh_key_path():
    home = os.path.expanduser("~")
    ssh_dir = os.path.join(home, ".ssh")

    default_keys = ["id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"]

    for key in default_keys:
        key_path = os.path.join(ssh_dir, key)
        if os.path.isfile(key_path):
            verbose(f"Found ssh key file ({key_path})")
            return key_path

    verbose("No ssh key file found")
    return None


def parse_url_path_arg(arg):
    # Try to detect an SSH style URL
    pattern = "((?P<username>[^@]*)@)?(?P<hostname>[^:]*)(?P<port>[0-9]{1,7})?:(?P<path>.*)"
    if match := re.match(pattern, arg):
        verbose("Found SSH-like")
        key_filename = get_default_ssh_key_path()
        pw = None
        while pw is None:
            pw = getpass.getpass(prompt=f"Password for key {key_filename}: ")
            try:
                key = RSAKey.from_private_key_file(key_filename, password=pw)
            except:
                print(" |> Invalid password...")
                pw = None
        verbose("Password correct.")

        return SshPath(
            user=match.group("username"),
            hostname=match.group("hostname"),
            path=match.group("path"),
            port=int(match.group("port")) if match.group("port") else 22,
            ssh_pkey=key,
        )

    # Try to detect an URL
    url = urlparse(arg)
    if url.netloc and not url.path:
        if not url.scheme:
            url = urlparse(f"http://{arg}")
        verbose("Found URL-like")
        return UrlPath(
            hostname=url.hostname,
            port=url.port,
            path=url.path
        )

    verbose("Found local path")
    # Fallback case: Local path to file
    return LocalPath(path=arg)


if __name__ == "__main__":
    # Define the path for the source and destination socket files
    verbose(" |> Parsing source arg...")
    source_socket_path = parse_url_path_arg(sys.argv[1])
    verbose(" |> Parsing dest args...")
    destination_socket_path = parse_url_path_arg(sys.argv[2])

    if not isinstance(source_socket_path, LocalPath):
        print("Unsupported source file path!" +
              " Please use a local file path instead")
        exit(1)

    # Ensure the socket file does not already exist
    verbose(" |> Ensuring socket file does not exist...")
    if os.path.exists(source_socket_path.path):
        verbose("File exists, unlinking...")
        os.unlink(source_socket_path.path)

    print(" |> Starting listen and relay instance...")
    listen_and_relay(source_socket_path, destination_socket_path)
