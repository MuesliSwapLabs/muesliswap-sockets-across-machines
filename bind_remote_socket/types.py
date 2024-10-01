import threading
import subprocess
import getpass
import time
import os
import shlex

from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
from paramiko import SSHClient, AutoAddPolicy, PasswordRequiredException, RSAKey

from . import get_default_ssh_key_path, wrap_terminate_on_exit
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
        print(len(self.temp_pw or ""))
        try:
            RSAKey.from_private_key_file(key_filename, password=self.temp_pw)
        except PasswordRequiredException:
            # We are using a frozen dict, but I want to remember this PW
            object.__setattr__(self, "temp_pw",
                               getpass.getpass(prompt=f"Password for key {key_filename}: "))

        print(len(self.temp_pw or ""))

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
            pkey = RSAKey.from_private_key_file(key_filename, password=self.temp_pw)

            ssh.connect(self.hostname, port=self.port, username=self.user, pkey=pkey)

            # Run the server side socat command, and ensure it's properly
            # cleaned up when the SSH connection is closed
            print(" /> Starting server side socat instance")

            def run_remote_socat():
                command = f'sudo socat "UNIX-CONNECT:{self.path}" "TCP-LISTEN:{self.temp_port_src},fork,reuseaddr"'
                print(f" /socat server> Running Command: {command}")
                
                # Run the command on the remote server
                stdin, stdout, stderr = ssh.exec_command(command)

                # Function to log output from a stream (stdout or stderr)
                def log_stream(stream, label):
                    for line in iter(stream.readline, ""):
                        if line:  # Only log if line is not empty
                            print(f" |  {label}: {line.strip()}")

                # Create separate threads for stdout and stderr to read them simultaneously
                stdout_thread = threading.Thread(target=log_stream, args=(stdout, "STDOUT"))
                stderr_thread = threading.Thread(target=log_stream, args=(stderr, "STDERR"))

                # Start the threads
                stdout_thread.start()
                stderr_thread.start()

                # Wait for both threads to complete
                stdout_thread.join()
                stderr_thread.join()

                print(" |  Remote command finished.")


            remote_socat = threading.Thread(target=run_remote_socat)
            remote_socat.daemon = True
            remote_socat.start()




            print(" /> Starting tunnel between server and client")
            # Map remote port to localhost (in case ports are not opened publicly)
            print(f"dst port: {self.temp_port_dst}; src port: {self.temp_port_src}")
            forward_tunnel(
                self.temp_port_dst,
                '127.0.0.1',
                self.temp_port_src,
                ssh.get_transport()
            )

            # Run the client side socat command and ensure it's properly cleaned up
            # when the process is terminated
            print(" /> Starting the client side socat instance")
            def run_socat_client_side():
                client_command = f'socat -d "TCP:localhost:{self.temp_port_dst}" "UNIX-LISTEN:{self.temp_file},fork,unlink-early"'
                print(f" /socat client> Running Command: {client_command}")
                process = subprocess.Popen(
                    shlex.split(client_command),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,  # Ensure output is in text mode, not binary
                    bufsize=1   # Line-buffered output
                )
                # result = subprocess.run(shlex.split(client_command))
                # print(" |  STDOUT:")
                # print(result.stdout)
                # print(" |  STDERR:")
                # print(result.stderr)
                # Continuously read from stdout and stderr
                with process.stdout, process.stderr:
                    for line in iter(process.stdout.readline, ''):
                        print(f" |  STDOUT: {line.strip()}")
                    for line in iter(process.stderr.readline, ''):
                        print(f" |  STDERR: {line.strip()}")

                # Wait for the process to complete
                process.wait()
                print(" |  Socat client process finished.")

            client_socat_thread = threading.Thread(target=run_socat_client_side)
            client_socat_thread.daemon = True  # Use a daemon thread to allow clean exit
            client_socat_thread.start()

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
