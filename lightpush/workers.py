import collections
import socket

from lightpush.http import (websocket_response, http_response,
                            HttpRequest)


class Worker(object):
    is_reader = False
    is_writer = False
    is_client = False

    def __init__(self):
        self.server = None
        self.sock = None

    def fileno(self):
        return self.sock.fileno()

    def close(self):
        self.server.remove(self)
        self.sock.close()


class Listener(Worker):
    is_reader = True

    def __init__(self, server, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.setblocking(0)
        self.sock.bind((host, port))
        self.sock.listen(5)

        self.server = server
        self.server.add(self)

    def read(self):
        conn, addr = self.sock.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        conn.setblocking(0)

        print("Client connected @%s:%s" % (addr[0], addr[1]))
        self.server.add(Handshaker(self.server, conn, addr))


class Handshaker(Worker):
    is_reader = True
    is_writer = True

    def __init__(self, server, sock, addr):
        self.server = server
        self.sock = sock
        self.addr = addr
        self.request = HttpRequest()

        self.is_request_received = False

    def read(self):
        if self.is_request_received:
            return

        data = self.sock.recv(4096)
        self.request.feed(data)

        if not self.request.is_complete:
            return

        try:
            if self.request.is_websocket():
                self.response = websocket_response(self.request)
            elif self.request.token() == self.server.key:
                channel = self.request.parser.get_path()
                self.server.broadcast(channel, self.request.body)
                self.response = http_response(self.request, 200)
            else:
                self.response = http_response(self.request, 401)
        except Exception as e: # TODO: Better error handling
            raise e

        self.is_request_received = True

    def write(self):
        if not self.is_request_received:
            return

        nsent = self.sock.send(self.response)
        self.response = self.response[nsent:]

        if not self.response:
            self.server.remove(self)

            if self.request.is_websocket():
                channel = self.request.parser.get_path()
                client = Client(self.server, self.sock, self.addr, channel)
                self.server.add(client)
            else:
                self.sock.close()


class Client(Worker):
    is_writer = True
    is_client = True

    def __init__(self, server, sock, addr, channel):
        self.server = server
        self.sock = sock
        self.addr = addr
        self.channel = channel

        self.buffer = None
        self.queue = collections.deque([])

    def enqueue(self, packet):
        self.queue.append(packet)

    def write(self):
        if not self.buffer:
            try:
                self.buffer = self.queue.popleft()
            except IndexError: # Queue is empty
                pass

        if self.buffer:
            nsent = self.sock.send(self.buffer)
            self.buffer = self.buffer[nsent:]
