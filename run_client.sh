#!/usr/bin/env bash

RAND_STR=$(date +%s)
# Config
# TODO pjordan: Move this to an env file and source it here instead!
SERVER_USER=trim
SERVER_ADDRESS=onchain.muesliswap.com
SERVER_PORT=18823
SERVER_SOCKET_PATH=/home/cardano/cardano-node/db/socket

CLIENT_PORT=18823
CLIENT_SOCKET_PATH=./temp.socket

# Check if socat is installed
if ! which socat &> /dev/null; then
    echo "SOCAT is not installed!!"
    echo "Please install socat first, to use this script"
    exit 1
fi

if ! ssh "$SERVER_USER@$SERVER_ADDRESS" which socat; then
    echo "SOCAT is not installed on remote host!!"
    echo "Please install socat first on the remote, to use this script"
    exit 1
fi

function map_remote() {
  echo "|> Starting socat on remote host"
  ssh "$SERVER_USER@$SERVER_ADDRESS" /bin/bash << EOF
  sudo socat "UNIX-SENDTO:$SERVER_SOCKET_PATH,bind=/tmp/comm-socket-$RAND_STR" "TCP-LISTEN:$SERVER_PORT"
EOF
}

function connect_remote_client() {
  echo "|> Mapping remote host socat port to localhost"
  ssh -L "$CLIENT_PORT:localhost:$SERVER_PORT" -N -T "$SERVER_USER@$SERVER_ADDRESS"
}

function map_client() {
  echo "|> Mapping localhost port to socket file"
  socat "TCP:localhost:$CLIENT_PORT" "UNIX-RECVFROM:$CLIENT_SOCKET_PATH"
}

# Step 1: Start socat on remote and map to port
map_remote &
sleep 3
# Step 2: Map socket port to local machine
connect_remote_client &
sleep 3
# Step 3: Map port to socket on local machine
map_client &
sleep 3

read -rp "Press Enter to terminate" </dev/tty
