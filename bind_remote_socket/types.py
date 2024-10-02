import threading
import subprocess
import time
import os
import shlex

from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
from paramiko import SSHClient, AutoAddPolicy, PasswordRequiredException, RSAKey
from typing import Any

from .forwarder import forward_tunnel
from .socat import run_remote_socat, run_socat_client_side

from . import VERBOSE_TYPES

def verbose(s):
    if VERBOSE_TYPES:
        print(f" |> {s}")

class CustomPath:
    def get_path(self):
        raise NotImplementedError

@dataclass(frozen=True)
class LocalPath(CustomPath):
    path: str

    def get_path(self):
        return path

@dataclass(frozen=True)
class UrlPath(CustomPath):
    path: str
    hostname: str
    port: int

    def get_path(self):
        return (hostname, port)


@dataclass(frozen=True)
class SshPath(CustomPath):
    path: str
    hostname: str
    port: int
    user: str

    ssh_pkey: Any

    temp_port_src = 4041
    temp_port_dst = 4042
    temp_file = "/tmp/muesli-sam.socket"

    @contextmanager
    def get_path(self):
        ssh = None
        ssh_tunnel = None
        try:
            # Create a new socket mapping from the remote host to a local file

            # Open a ssh connection
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(AutoAddPolicy())

            ssh.connect(self.hostname, port=self.port, username=self.user, pkey=self.ssh_pkey)

            # Run the server side socat command, and ensure it's properly
            # cleaned up when the SSH connection is closed
            print(" |> Starting server side socat instance")
            error_event = threading.Event()
            server_socat_ready = threading.Event()
            remote_socat = threading.Thread(target=run_remote_socat, args=(ssh, self.path, self.temp_port_src, server_socat_ready, error_event))
            remote_socat.daemon = True
            remote_socat.start()

            verbose(" |> Waiting for socat (server side) to be ready")
            while not server_socat_ready.is_set():
                time.sleep(0.5)
                if error_event.is_set():
                    verbose(" |> Socat (server side) did not start up properly...")
                    exit(1)

            print(" |> Starting tunnel between server and client")
            # Map remote port to localhost (in case ports are not opened publicly)
            ssh_tunnel = forward_tunnel(
                self.temp_port_dst,
                '127.0.0.1',
                self.temp_port_src,
                ssh.get_transport()
            )

            # Run the client side socat command and ensure it's properly cleaned up
            # when the process is terminated
            client_socat_ready = threading.Event()
            client_socat_thread = threading.Thread(target=run_socat_client_side, args=(self.temp_port_dst, self.temp_file, client_socat_ready, error_event))
            client_socat_thread.daemon = True  # Use a daemon thread to allow clean exit
            client_socat_thread.start()

            verbose(" |> Waiting for socat (client side) to be ready")
            while not client_socat_ready.is_set():
                time.sleep(0.5)
                if error_event.is_set():
                    verbose(" |> Socat (client side) did not start up properly...")
                    exit(1)

            # Wait until the temp_socket file has been created
            verbose(" |> Waiting for socket file to be created")
            timeout = 20
            start_time = time.time()
            while not os.path.exists(self.temp_file):
                time.sleep(0.1)
                if timeout and (time.time() - start_time) > timeout:
                    raise TimeoutError(f"Timeout waiting for file: {self.temp_file}")
            
            verbose(" |> Socket file created!")
            yield (self.temp_file)
        finally:
            print(" |> Cleaning up connection...")
            # Close the SSH connection
            if ssh: ssh.close()
            # Close the SSH tunnel
            if ssh_tunnel: ssh_tunnel.shutdown()
