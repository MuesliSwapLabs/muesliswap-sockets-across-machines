from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
from paramiko import SSHClient, AutoAddPolicy, PasswordRequiredException, RSAKey
from sshtunnel import SSHTunnelForwarder
import subprocess
import getpass
import time
import os
import shlex

from . import get_default_ssh_key_path, wrap_terminate_on_exit

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

    temp_port_src = 4041
    temp_port_dst = 4042
    temp_file = "/tmp/muesli-sam.socket"
    temp_pw = None

    def __post_init__(self):
        key_filename = get_default_ssh_key_path()
        try:
            RSAKey.from_private_key_file(key_filename, password=self.temp_pw)
        except PasswordRequiredException:
            # We are using a frozen dict, but I want to remember this PW
            object.__setattr__(self, "temp_pw",
                               getpass.getpass(prompt=f"Password for key {key_filename}: "))


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

            key_filename = get_default_ssh_key_path()
            private_key = RSAKey.from_private_key_file(key_filename, password=self.temp_pw)

            ssh.connect(self.hostname, port=self.port, username=self.user, pkey=private_key)

            print(" /> Starting server side socat instance")
            # Run the server side socat command, and ensure it's properly
            # cleaned up when the SSH connection is closed
            remote_command = f'sudo socat "UNIX-CONNECT:{self.path}" "TCP-LISTEN:{self.temp_port_src},fork,reuseaddr"'

            _, stdout, stderr = ssh.exec_command(wrap_terminate_on_exit(remote_command))
            print(" |  STDOUT:")
            print(stdout)
            print(" |  STDERR:")
            print(stderr)


            # Map remote port to localhost (in case ports are not opened publicly)
            # tunnel = SSHTunnelForwarder(
            #     (self.hostname, self.port),
            #     ssh_username=self.user,
            #     ssh_password=self.temp_pw,
            #     remote_bind_address=('127.0.0.1', self.temp_port_src),
            #     local_bind_address=('0.0.0.0', self.temp_port_dst),
            #     ssh_pkey=key_filename,
            #     ssh_private_key_password=self.temp_pw,
            # )
            print(" /> Starting tunnel between server and client")
            result = subprocess.Popen([
              "ssh", "-L", f"{self.temp_port_src}:localhost:{self.temp_port_dst}", "-N", 
              "-T" ,f"{self.user}@{self.hostname}", '&'
            ])
            print(" |  STDOUT:")
            print(result.stdout)
            print(" |  STDERR:")
            print(result.stderr)

            # Run the client side socat command and ensure it's properly cleaned up
            # when the process is terminated
            print(" /> Starting the client side socat instance")
            client_command = f'socat -d "TCP:localhost:{self.temp_port_dst}" "UNIX-LISTEN:{self.temp_file},fork,unlink-early"'
            result = subprocess.run(shlex.split(wrap_terminate_on_exit(client_command)))
            print(" |  STDOUT:")
            print(result.stdout)
            print(" |  STDERR:")
            print(result.stderr)

            # Wait until the temp_socket file has been created
            print(" /> Waiting for socket file to be created")
            timeout = 20
            start_time = time.time()
            while not os.path.exists(self.temp_file):
                time.sleep(0.1)
                if timeout and (time.time() - start_time) > timeout:
                    raise TimeoutError(f"Timeout waiting for file: {self.temp_file}")
            
            yield (self.temp_file)
        finally:
            print(" |> Cleaning up...")
            # Close the port tunnel
            if tunnel: tunnel.close()
            # Close the SSH connection
            if ssh: ssh.close()
