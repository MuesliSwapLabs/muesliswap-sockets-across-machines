import threading
import time
import os

from dataclasses import dataclass
from contextlib import contextmanager
from paramiko import (
    SSHClient, AutoAddPolicy
)
from typing import Any

from .forwarder import forward_tunnel
from .socat import run_remote_socat, run_socat_client_side, kill_on_remote_port

from . import VERBOSE_TYPES


def verbose(s):
    if VERBOSE_TYPES:
        print(s)


class CustomPath:
    def get_path(self):
        raise NotImplementedError


@dataclass(frozen=True)
class LocalPath(CustomPath):
    path: str

    def get_path(self):
        return self.path


@dataclass(frozen=True)
class UrlPath(CustomPath):
    path: str
    hostname: str
    port: int

    def get_path(self):
        return (self.hostname, self.port)


@dataclass(frozen=True)
class SshPath(CustomPath):
    path: str
    hostname: str
    port: int
    user: str

    ssh_pkey: Any

    _counter = 0
    _port_src = 4041
    _port_dst = 4042
    temp_file = "/tmp/muesli-sam.socket"

    @contextmanager
    def get_path(self, use_sudo=False):
        # Rotate through multiple ports, to account for connection teardown
        counter = self._counter
        object.__setattr__(self, "_counter", (self._counter + 1) % 10)
        port_src = self._port_src + counter
        port_dst = self._port_dst + counter

        ssh = None
        ssh_tunnel = None
        remote_socat = None
        try:
            # Create a new socket mapping from the remote host to a local file

            # Open a ssh connection
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(AutoAddPolicy())

            ssh.connect(self.hostname, port=self.port,
                        username=self.user, pkey=self.ssh_pkey)

            # Run the server side socat command, and ensure it's properly
            # cleaned up when the SSH connection is closed
            print(" |> Starting server side socat instance")
            use_sudo_on_remote = "SAM_USE_SUDO_REMOTE" in os.environ and \
                os.environ["SAM_USE_SUDO_REMOTE"]
            error_event = threading.Event()
            server_socat_ready = threading.Event()
            remote_socat = threading.Thread(target=run_remote_socat, args=(
                ssh, self.path, port_src,
                server_socat_ready, error_event, use_sudo_on_remote
            ))
            remote_socat.daemon = True
            remote_socat.start()

            verbose(" |> Waiting for socat (server side) to be ready")
            while not server_socat_ready.is_set():
                time.sleep(0.5)
                if error_event.is_set():
                    verbose(
                        " |> Socat (server side) did not start up properly..."
                    )
                    exit(1)

            print(" |> Starting tunnel between server and client")
            # Map remote port to localhost
            # (in case ports are not opened publicly)
            ssh_tunnel = forward_tunnel(
                port_dst,
                '127.0.0.1',
                port_src,
                ssh.get_transport()
            )

            # Run the client side socat command and ensure it's properly
            # cleaned up when the process is terminated
            use_sudo_on_client = "SAM_USE_SUDO_CLIENT" in os.environ and \
                os.environ["SAM_USE_SUDO_CLIENT"]
            client_socat_ready = threading.Event()
            client_socat_thread = threading.Thread(
                target=run_socat_client_side, args=(
                    port_dst, self.temp_file, client_socat_ready,
                    error_event, use_sudo_on_client
                ))
            # Use a daemon thread to allow clean exit
            client_socat_thread.daemon = True
            client_socat_thread.start()

            verbose(" |> Waiting for socat (client side) to be ready")
            while not client_socat_ready.is_set():
                time.sleep(0.5)
                if error_event.is_set():
                    verbose(
                        " |> Socat (client side) did not start up properly..."
                    )
                    exit(1)

            # Wait until the temp_socket file has been created
            verbose(" |> Waiting for socket file to be created")
            timeout = 20
            start_time = time.time()
            while not os.path.exists(self.temp_file):
                time.sleep(0.1)
                if timeout and (time.time() - start_time) > timeout:
                    raise TimeoutError(
                        f"Timeout waiting for file: {self.temp_file}")

            verbose(" |> Socket file created!")
            yield (self.temp_file)
        finally:
            print(" |> Cleaning up connection...")
            # Close the SSH tunnel
            if ssh_tunnel:
                verbose(" |> Closing ssh tunnel")
                ssh_tunnel.shutdown()
            # Close socat
            if remote_socat.is_alive():
                verbose(" |> Killing socat")
                errors = kill_on_remote_port(ssh, port_src)
                if errors:
                    verbose(f" |> Got errors: {errors}")
            # Close the SSH connection
            if ssh:
                verbose(" |> Closing ssh client")
                ssh.close()
