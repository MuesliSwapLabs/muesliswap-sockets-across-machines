import select
import threading

try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer

import paramiko


g_verbose = True
def verbose(s):
    if g_verbose:
        print(s)

class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            chan = self.ssh_transport.open_channel(
                "direct-tcpip",
                (self.chain_host, self.chain_port),
                self.request.getpeername(),
            )
        except Exception as e:
            verbose(
                "Incoming request to %s:%d failed: %s"
                % (self.chain_host, self.chain_port, repr(e))
            )
            return
        if chan is None:
            verbose(
                "Incoming request to %s:%d was rejected by the SSH server."
                % (self.chain_host, self.chain_port)
            )
            return

        verbose(
            "Connected!  Tunnel open %r -> %r -> %r"
            % (
                self.request.getpeername(),
                chan.getpeername(),
                (self.chain_host, self.chain_port),
            )
        )
        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)

        peername = self.request.getpeername()
        chan.close()
        self.request.close()
        verbose("Tunnel closed from %r" % (peername,))


# def forward_tunnel(local_port, remote_host, remote_port, transport):
#     # this is a little convoluted, but lets me configure things for the Handler
#     # object.  (SocketServer doesn't give Handlers any way to access the outer
#     # server normally.)
#     class SubHander(Handler):
#         chain_host = remote_host
#         chain_port = remote_port
#         ssh_transport = transport
# 
#     ForwardServer(("", local_port), SubHander).serve_forever()


def forward_tunnel(local_port, remote_host, remote_port, transport):
    class SubHandler(Handler):
        chain_host = remote_host
        chain_port = remote_port
        ssh_transport = transport

    server = ForwardServer(("", local_port), SubHandler)

    # Run the server in a separate thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True  # Use a daemon thread to allow clean exit
    server_thread.start()

    print(f"Started tunnel on localhost:{local_port} -> {remote_host}:{remote_port}")

    # Return the server object so you can manage it (e.g., shut it down later)
    return server
