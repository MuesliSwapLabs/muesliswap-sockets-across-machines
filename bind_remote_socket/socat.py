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
from . import VERBOSE_SOCAT, DEBUG_SOCAT


_debug_flag = '-ddd' if DEBUG_SOCAT else ''

def verbose(s):
    if VERBOSE_SOCAT:
        print(s)

def kill_on_remote_port(ssh_client, port):
    pids = []
    (_,stdout,_) = ssh_client.exec_command(f"sudo lsof -i :{port}")
    for i, line in enumerate(iter(stdout.readline, "")):
        if i > 0: 
            ls = line.split()
            pids.append((ls[0], ls[1]))

    errors = []
    for (name, pid) in pids:
        if name == "socat":
            verbose(f"[SOCAT SERVER]> Killing socat instance...")
            ssh_client.exec_command(f"sudo kill -9 {pid}")
        else:
            errors.append(name)
    return errors

def run_remote_socat(ssh_client, path, port, ready_event, error_event):
    print(" |> Starting the server side socat instance")
    verbose(f"[SOCAT SERVER]> Checking remote...")
    command = f'sudo socat {_debug_flag} UNIX-CONNECT:{path} TCP-LISTEN:{port},fork,reuseaddr'

    verbose(f"[SOCAT SERVER]> Killing left over socat instance...")
    errors = kill_on_remote_port(ssh_client, port)
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
            verbose(f"[SOCAT SERVER]{label}> {line.strip()}")
    
    # Run the command on the remote server
    verbose(f"[SOCAT SERVER]> Running Command: {command}")
    stdin, stdout, stderr = ssh_client.exec_command(command)

    # Logging
    stdout_thread = threading.Thread(target=log_stream, args=(stdout,))
    stdout_thread.start()

    ready_event.set()

    for line in iter(stderr.readline, ""):
        verbose(f"[SOCAT SERVER](ERR) {line.strip()}")

    stdout_thread.join()

    verbose("[SOCAT SERVER]> Instance terminated.")

def run_socat_client_side(port, file, ready_event, error_event):
    print(" |> Starting the client side socat instance")
    client_command = f'socat {_debug_flag} "TCP:localhost:{port}" "UNIX-LISTEN:{file},fork,unlink-early"'
    verbose(f"[SOCAT CLIENT]> Running Command: {client_command}")
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
            verbose(f"[SOCAT CLIENT]{label}> {line.strip()}")

    stdout_thread = threading.Thread(target=log_stream, args=(process.stdout,))

    with process.stderr:
        for line in iter(process.stderr.readline, ''):
            if not line: continue
            verbose(f"[SOCAT CLIENT](ERROR)> {line.strip()}")


    # Wait for the process to complete
    process.wait()
    verbose("[SOCAT CLIENT]> Instance terminated.")
