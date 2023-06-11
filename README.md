# Muesliswap SAM
## Sockets-Across-Machines

Inspired by [cardano-node-socket-over-https](https://gimbalabs.com/dandelion/endpoints/cardano-node-socket)

Basically a set of scripts that allows one to relatively easily map sockets via ssh between a server and a client that needs access to the corresponding socket.
This was made with Cardano Sockets in mind, but in theory can be generalized quite a bit.

## Setup

Make sure socat is installed on your client and server.
Additionally ensure that you have passwordless sudo access on the server.
Copy the `ENV\_TEMPLATE` file to `ENV` and fill in the required information.

## Running

Simply execute `./bind_remote_socket.sh`
After everything is setup simply press enter to terminate the connection.
Beware that currently the remote port is opened publicly (unless otherwise specified by a firewall), which might give outsiders unwanted access to your node.


## FAQ

### Do I really need passwordless sudo on the remote?
No, you don't necessarily. If you are sure that the permissions of the socket file you are trying to map allow your login user to read and write to and from the socket file, feel free to adapt the script to no longer use sudo.
You can simply remove the sudo prefix in the map\_remote function.

