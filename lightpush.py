import os
import re
import json
import base64
import socket
import select
import hashlib
import argparse
import collections


__version__ = "0.1.0"


RESPONSE_OPTIONS = '\r\n'.join([
    "HTTP/1.1 200 OK",
    "Allow: OPTIONS, GET, POST",
    "Access-Control-Allow-Origin: *",
    "Access-Control-Allow-Methods: OPTIONS, GET, POST",
    "Access-Control-Allow-Headers: Authorization, Lightpush-Message",
    ""
])


RESPONSE_202_ACCEPTED = '\r\n'.join([
    "HTTP/1.1 202 Accepted",
    "Access-Control-Allow-Origin: *",
    "Access-Control-Allow-Methods: OPTIONS, GET, POST",
    "Access-Control-Allow-Headers: Authorization, Lightpush-Message",
    "",
    "",
    "{ \"message\": \"{message}\" }",
    "",
    ""
])


RESPONSE_400_BAD_REQUEST = '\r\n'.join([
    "HTTP/1.1 400 Bad Request",
    "Access-Control-Allow-Origin: *",
    "Access-Control-Allow-Methods: OPTIONS, GET, POST",
    "Access-Control-Allow-Headers: Authorization, Lightpush-Message",
    "",
    "",
    "{ \"message\": \"{message}\" }",
    "",
    ""
])


RESPONSE_401_UNAUTHORIZED = '\r\n'.join([
    "HTTP/1.1 401 Unauthorized",
    "WWW-Authenticate: Secret-Key",
    "Access-Control-Allow-Origin: *",
    "Access-Control-Allow-Methods: OPTIONS, GET, POST",
    "Access-Control-Allow-Headers: Authorization, Lightpush-Message",
    "",
    "",
    "{ \"message\": \"{message}\" }",
    "",
    ""
])


RESPONSE_403_FORBIDDEN = '\r\n'.join([
    "HTTP/1.1 403 Forbidden",
    "Access-Control-Allow-Origin: *",
    "Access-Control-Allow-Methods: OPTIONS, GET, POST",
    "Access-Control-Allow-Headers: Authorization, Lightpush-Message",
    "",
    "",
    "{ \"message\": \"{message}\" }",
    "",
    ""
])


RESPONSE_WEBSOCKET = '\r\n'.join([
    "HTTP/1.1 101 Switching Protocols",
    "Upgrade: websocket",
    "Connection: Upgrade",
    "Sec-WebSocket-Accept: {0}",
    "",
    ""
])



class HttpRequest(object):
    _request_line_pattern = r"^(?P<method>GET|POST|OPTIONS) (?P<request_uri>[^\s]+) (?P<http_version>HTTP/1.1)$"
    _header_pattern = r"^(?P<header_name>[^:]+):(?P<header_value>.+)$"

    def __init__(self, req):
        self.is_valid = False
        self.headers = {}
        _lines = req.split("\r\n")
        _match = re.match(self._request_line_pattern, _lines[0])
        _lines = _lines[1:-2]
        if _match is None:
            return
        _gdict = _match.groupdict()
        self.method = _gdict["method"]
        self.request_uri = _gdict["request_uri"]
        self.http_version = _gdict["http_version"]
        for line in _lines:
            _match = re.match(self._header_pattern, line)
            if _match is None:
                return
            _gdict = _match.groupdict()
            self.headers[_gdict["header_name"]] = _gdict["header_value"].strip()
        self.is_valid = True


## Uses select.poll()
class Server(object):
    def __init__(self):
        self._poller = select.poll()
        self._sockets = {}
        self._clients = []

    def add_socket(self, sock):
        # constructing event mask
        mask = (select.POLLERR | select.POLLHUP)
        if sock.is_readable:
            mask = mask | (select.POLLIN | select.POLLPRI)
        if sock.is_writeable:
            mask = mask | select.POLLOUT
        # registering socket
        self._poller.register(sock, mask)
        self._sockets[sock.fileno()] = sock
        if isinstance(sock, ClientSocket):
            self._clients.append(sock)

    def remove_socket(self, sock):
        self._poller.unregister(sock)
        self._sockets.pop(sock.fileno())
        if isinstance(sock, ClientSocket):
            self._clients.remove(sock)

    def handle_events(self):
        events = self._poller.poll()
        for fd, event in events:
            try:
                sock = self._sockets[fd]
                if event & select.POLLHUP:
                    sock.on_close()
                if event & select.POLLERR:
                    sock.on_error()
                if event & (select.POLLIN | select.POLLPRI):
                    sock.on_read()
                if event & select.POLLOUT:
                    sock.on_write()
            except socket.error:
                print "Error with a socket. Closing the connection"
                self.remove_socket(sock)

    def broadcast(self, message):
        msg = bytearray(message)
        msg.insert(0, len(msg))
        msg.insert(0, 129)
        for client in self._clients:
            client.enqueue(msg)


class BaseSocket(object):
    def __init__(self, server, sock, addr):
        self.is_readable = False
        self.is_writeable = False
        self.server = server
        self.socket = sock
        self.address = addr
        self.initialize()
        self.server.add_socket(self)

    def fileno(self):
        return self.socket.fileno()

    def initialize(self):
        pass

    def on_read(self):
        return NotImplementedError

    def on_write(self):
        return NotImplementedError

    def on_close(self):
        return NotImplementedError

    def on_error(self):
        return NotImplementedError


class ListenerSocket(BaseSocket):
    def initialize(self):
        self.is_readable = True

    def on_read(self):
        conn, addr = self.socket.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        conn.setblocking(0)
        HandshakeSocket(self.server, conn, addr)


class HandshakeSocket(BaseSocket):
    def initialize(self):
        self.is_readable = True
        self.chunk_count = 0
        self.chunks = []

    def terminate(self):
        self.server.remove_socket(self)
        self.socket.close()

    def construct_response(self):
        # By default, the connection is closed after sending the response
        # The only exception is successful websocket handshake
        self.close_after_send = True
        self.is_websocket = False
        request = HttpRequest(''.join(self.chunks))
        self.is_valid = request.is_valid
        if not self.is_valid:
            return
        if request.method == "OPTIONS":
            self.response = RESPONSE_OPTIONS
            return
        elif request.method == "GET":
            websocket_key = request.headers.get("Sec-WebSocket-Key", None)
            if websocket_key is None:
                self.response = RESPONSE_400_BAD_REQUEST
                return
            self.is_websocket = True
            self.close_after_send = False
            sha = hashlib.sha1(websocket_key+WEBSOCKET_MAGIC_STRING) # pylint: disable=E1101, C0301
            accept = base64.b64encode(sha.digest())
            self.response = RESPONSE_WEBSOCKET.format(accept)
        elif request.method == "POST":
            secret_key = request.headers.get("Authorization", None)
            if secret_key is None:
                self.response = RESPONSE_401_UNAUTHORIZED
                return
            message = request.headers.get("Lightpush-Message", None)
            if message is None:
                self.response = RESPONSE_400_BAD_REQUEST
                return
            if secret_key != SECRET_KEY:
                self.response = RESPONSE_403_FORBIDDEN
                return
            self.response = RESPONSE_202_ACCEPTED
            self.server.broadcast(message)


    def on_read(self):
        new_chunk = self.socket.recv(READ_CHUNK_SIZE)
        self.chunks.append(new_chunk)
        self.chunk_count += 1
        if (new_chunk[-4:] == "\r\n\r\n"):
            self.construct_response()
            if self.is_valid:
                self.server.remove_socket(self)
                self.is_writeable = True
                self.is_readable = False
                self.server.add_socket(self)
            else: # Unrecognized handshake
                return self.terminate()
        elif (self.chunk_count > MAX_CHUNK_COUNT):
            return self.terminate()
        else:
            pass # Continue to read

    def on_write(self):
        self.response = self.response[self.socket.send(self.response):]
        if self.response == "": # Finished sending
            if self.close_after_send:
                return self.terminate()
            else:
                self.server.remove_socket(self)
                if self.is_websocket:
                    ClientSocket(self.server, self.socket, self.address)
                else:
                    raise NotImplementedError("This shouldn't have happened.")


class RemoteConnectionSocket(BaseSocket):
    def initialize(self):
        self.is_readable = True
        self.size = 0
        self.chunks = []

    def on_read(self):
        if self.size == 0:
            self.size = ord(self.socket.recv(1))
        else:
            new_chunk = self.socket.recv(self.size)
            self.chunks.append(new_chunk)
            self.size = self.size - len(new_chunk)
            if self.size == 0:
                message = ''.join(self.chunks)
                self.chunks = []
                self.server.broadcast(message)


class ClientSocket(BaseSocket):
    def initialize(self):
        self.is_writeable = True
        self.buffer = bytearray("")
        self.queue = collections.deque([])

    def enqueue(self, message):
        self.queue.append(message)

    def on_write(self):
        if self.buffer == "":
            try:
                self.buffer = self.queue.popleft()
            except IndexError: # Queue is empty
                pass
        self.buffer = self.buffer[self.socket.send(self.buffer):]


class Connection(object):
    def __init__(self, host, port, secret_key):
        self.host = host
        self.port = port
        self.secret_key = secret_key

    def connect(self):
        request = json.dumps({ "secret_key": self.secret_key }) + "\r\n\r\n"
        self.socket = socket.socket()
        self.socket.connect((self.host, self.port))
        self.socket.send(request)
        response = self.socket.recv(4)
        return response
    
    def send(self, message):
        b = bytearray(message)
        b.insert(0, len(b))
        self.socket.send(b)

    def close(self):
        self.socket.close()


if __name__ == "__main__":
    # ------------------------ Default Configuration ------------------------ #
    HOST = ""
    PORT = 8086
    SECRET_KEY = "29e03fe7-9e8f-42b2-a9ac-2c9519bdf0b1"
    WEBSOCKET_MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    TIMEOUT = 100
    BACKLOG = 5
    READ_CHUNK_SIZE = 4096
    MAX_CHUNK_COUNT = 16
    # For debugging purposes
    # READ_CHUNK_SIZE = 40
    # MAX_CHUNK_COUNT = 40


    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Arguments ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default=HOST,
        help="Specify a custom host name for the server. \
        Defaults to empty string which means any host name.")
    parser.add_argument("--port", type=int, default=PORT,
        help="Specify a custom port to run the server. \
        Defaults to 8086 if not specified")
    parser.add_argument("--secret-key", type=str, default=SECRET_KEY,
        help="Specify the secret key that is used to identify \
        and authenticate remote server(s). See the official \
        documentation for the default value.")
    parser.add_argument("--verbosity", type=int, metavar="LEVEL",
        choices=(0, 1, 2, 3, 4), default=2,
        help="Specify the logging level for the server.")
    settings = parser.parse_args()
    SECRET_KEY = settings.secret_key


    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ Initial Logging ~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
    print "lightpush v{version}".format(version=__version__)
    print "pid: {pid}".format(pid=os.getpid())
    print "host: \'{host}\'".format(host=settings.host)
    print "port: {port}".format(port=settings.port)
    print "verbosity: {v}".format(v=settings.verbosity)
    print ""


    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ Initialization ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
    server = Server()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.setblocking(0)
    s.bind((settings.host, settings.port))
    s.listen(BACKLOG)
    listener = ListenerSocket(server, s, s.getsockname())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~ Almighty Event Loop ~~~~~~~~~~~~~~~~~~~~~~~~~ #
    while 1: server.handle_events()
