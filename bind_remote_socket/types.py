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


def run_remote_socat(ssh_client, path, port, ready_event, error_event):
    print(f"[SOCAT SERVER]> Checking remote...")
    command = f'sudo socat -ddd UNIX-CONNECT:{path} TCP-LISTEN:{port},fork,reuseaddr'

    check_pgrep = False
    pids = []
    (_,stdout,_) = ssh_client.exec_command(f"sudo lsof -i :{port}")
    for i, line in enumerate(iter(stdout.readline, "")):
        if i > 0: 
            ls = line.split()
            pids.append((ls[0], ls[1]))

    errors = []
    for (name, pid) in pids:
        if name == "socat":
            print(f"[SOCAT SERVER]> Killing leftover socat instance...")
            ssh_client.exec_command(f"sudo kill -9 {pid}")
        else:
            errors.append(name)
    if errors:
        print(f"[SOCAT SERVER](ERROR)> Port already in use by {errors}")
        error_event.set()
        exit(1)

    (_,_,stderr) = ssh_client.exec_command(f"sudo ls {path}")
    for i, line in enumerate(iter(stderr.readline, "")):
        if line and i > 0: 
            print(f"[SOCAT SERVER](ERROR)> Socket file does not exist.")
            error_event.set()
            exit(1)

    def log_stream(stream, label=""):
        for line in iter(stream.readline, ""):
            if not line: continue
            print(f"[SOCAT SERVER]{label}> {line.strip()}")
    
    # Run the command on the remote server
    print(f"[SOCAT SERVER]> Running Command: {command}")
    stdin, stdout, stderr = ssh_client.exec_command(command)

    # Logging
    stdout_thread = threading.Thread(target=log_stream, args=(stdout,))
    stdout_thread.start()

    ready_event.set()

    for line in iter(stderr.readline, ""):
        print(f"[SOCAT SERVER](ERR) {line.strip()}")

    stdout_thread.join()

    print("[SOCAT SERVER]>  Instance closed.")

def run_socat_client_side(port, file, ready_event, error_event):
    print(" /> Starting the client side socat instance")
    client_command = f'socat -ddd "TCP:localhost:{port}" "UNIX-LISTEN:{file},fork,unlink-early"'
    print(f"[SOCAT CLIENT]> Running Command: {client_command}")
    process = subprocess.Popen(
        shlex.split(client_command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,  # Ensure output is in text mode, not binary
        bufsize=1   # Line-buffered output
    )

    if process.returncode is None:
        ready_event.set()
    else:
        error_event.set()

    def log_stream(stream, label=""):
        for line in iter(stream.readline, ""):
            if not line: continue
            print(f"[SOCAT CLIENT]{label}> {line.strip()}")

    stdout_thread = threading.Thread(target=log_stream, args=(process.stdout,))

    with process.stderr:
        for line in iter(process.stderr.readline, ''):
            if not line: continue
            print(f"[SOCAT CLIENT](ERROR)> {line.strip()}")


    # Wait for the process to complete
    process.wait()
    print("[SOCAT CLIENT]> Command execution finished.")


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
        tunnel = None
        ssh = None
        try:
            # Create a new socket mapping from the remote host to a local file

            # Open a ssh connection
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(AutoAddPolicy())

            ssh.connect(self.hostname, port=self.port, username=self.user, pkey=self.ssh_pkey)

            # Run the server side socat command, and ensure it's properly
            # cleaned up when the SSH connection is closed
            print(" /> Starting server side socat instance")
            error_event = threading.Event()
            server_socat_ready = threading.Event()
            remote_socat = threading.Thread(target=run_remote_socat, args=(ssh, self.path, self.temp_port_src, server_socat_ready, error_event))
            remote_socat.daemon = True
            remote_socat.start()

            print(" /> Waiting for socat (server side) to be ready")
            while not server_socat_ready.is_set():
                time.sleep(0.5)
                if error_event.is_set():
                    print(" /> Socat (server side) did not start up properly...")
                    exit(1)

            print(" /> Starting tunnel between server and client")
            # Map remote port to localhost (in case ports are not opened publicly)
            forward_tunnel(
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

            print(" /> Waiting for socat (client side) to be ready")
            while not client_socat_ready.is_set():
                time.sleep(0.5)
                if error_event.is_set():
                    print(" /> Socat (client side) did not start up properly...")
                    exit(1)

            # Wait until the temp_socket file has been created
            print(" /> Waiting for socket file to be created")
            timeout = 20
            start_time = time.time()
            while not os.path.exists(self.temp_file):
                print(os.path.exists(self.temp_file))
                time.sleep(0.1)
                if timeout and (time.time() - start_time) > timeout:
                    raise TimeoutError(f"Timeout waiting for file: {self.temp_file}")
            
            print(" /> Socket file created!")
            yield (self.temp_file)
        finally:
            print(" |> Cleaning up...")
            # Close the port tunnel
            if tunnel: tunnel.close()
            # Close the SSH connection
            if ssh: ssh.close()
