#!/usr/bin/env bash

# Load Config
source ENV

# Check if socat is installed
if ! which socat &> /dev/null; then
    echo "SOCAT is not installed!!"
    echo "Please install socat first, to use this script"
    exit 1
fi

if ! ssh "$SERVER_USER@$SERVER_ADDRESS" which socat &> /dev/null; then
    echo "SOCAT is not installed on remote host!!"
    echo "Please install socat first on the remote, to use this script"
    exit 1
fi

function map_remote() {
  echo "|> Starting socat on remote host"
  ssh "$SERVER_USER@$SERVER_ADDRESS" "sudo socat \"UNIX-CONNECT:$SERVER_SOCKET_PATH\" \"TCP-LISTEN:$SERVER_PORT,fork,reuseaddr\""
}

function connect_remote_client() {
  echo "|> Mapping remote host socat port to localhost"
  ssh -L "$CLIENT_PORT:localhost:$SERVER_PORT" -N -T "$SERVER_USER@$SERVER_ADDRESS"
}

function map_client() {
  echo "|> Mapping localhost port to socket file"
  socat -d "TCP:localhost:$CLIENT_PORT" "UNIX-LISTEN:$CLIENT_SOCKET_PATH,fork,unlink-early"
}

# Step 1: Start socat on remote and map to port
map_remote &
PID_MAP_REMOTE=$!
sleep 3

# Step 2: Map socket port to local machine
connect_remote_client &
PID_CONNECT_REMOTE_CLIENT=$!
sleep 3

# Step 3: Map port to socket on local machine
map_client &
PID_MAP_CLIENT=$!
sleep 1

read -rp "Press Enter to terminate" </dev/tty

echo "|> Cleaning up"

# Kill everything from ssh and socat on the remote host
ssh "$SERVER_USER@$SERVER_ADDRESS" "sudo kill \$(sudo lsof -i :$SERVER_PORT | tail --lines +2 | awk '/socat/{ print \$2 }')"
ssh "$SERVER_USER@$SERVER_ADDRESS" "sudo kill \$(sudo lsof -i :$SERVER_PORT | tail --lines +2 | awk '/ssh/{ print \$2 }')"

# Kill everything from ssh and socat on the local host
kill $(lsof -i :$CLIENT_PORT | tail --lines +2 | awk '/socat/{ print $2 }')
kill $(lsof -i :$CLIENT_PORT | tail --lines +2 | awk '/ssh/{ print $2 }')
