# Muesliswap SAM
## Sockets-Across-Machines

Inspired by [cardano-node-socket-over-https](https://gimbalabs.com/dandelion/endpoints/cardano-node-socket)

A script that allows one to easily map sockets securely via ssh between a server and a client that needs access to the corresponding socket.
This was made with Cardano Sockets in mind, but in theory can be generalized quite a bit.

## Requirements
### Client
 * just
 * socat
 * python3
### Server
 * socat

## Setup & Usage
Make sure you fulfill the *Requirements* on both your client and server first, before continuing.
Additionally, it is currently a requirement to have password-less sudo access for the remote user.

 1. `just setup`
 2. `just run <REMOTE_NODE_SOCKET_PATH>`

This will create a local `node.socket` file, which can be used to interact with the cardano node.
 e.g. `just run user@my.server.com:/home/cardano/cardano-node/db/node.socket` would create a connection to the socket file located at `/home/cardano/cardano-node/db/node.socket` on the server `my.server.com`.


Be careful that the ports you choose are unused (especially not by another socat or ssh instance), as the script will kill remaining processes on these ports.

## FAQ

### Do I really need passwordless sudo on the remote?
No, you don't necessarily. If you are sure that the permissions of the socket file you are trying to map allow your login user to read and write to and from the socket file, feel free to adapt the script to no longer use sudo.

