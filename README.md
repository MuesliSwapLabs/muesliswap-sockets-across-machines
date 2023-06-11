# Muesliswap HTTPS Sockets

Inspired by [cardano-node-socket-over-https](https://gimbalabs.com/dandelion/endpoints/cardano-node-socket)

Basically a set of scripts that allows one to relatively easily map sockets via ssh between a server running a cardano node and a client that needs access to the corresponding socket

## Setup

Make sure socat is installed on your client and server.
Additionally ensure that you have passwordless sudo access on the server.
Copy the `ENV\_TEMPLATE` file to `ENV` and fill in the required information.

## Running

Simply execute `./run.sh`
After everything is setup simply press enter to terminate the connection.
(NOTE: Atm the script does not properly clean up, most things should fix themselves after a couple of minutes, but still)


## FAQ

### Do I really need passwordless sudo on the remote?
No, you don't necessarily. If you are sure that the permissions of the socket file you are trying to map allow your login user to read and write to and from the socket file, feel free to adapt the script to no longer use sudo.
You can simply remove the sudo prefix in the map\_remote function.
