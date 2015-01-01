import base64
import hashlib
from http_parser.pyparser import HttpParser


WEBSOCKET_MAGIC_STRING = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


class HttpRequest(object):
    def __init__(self):
        self.parser = HttpParser()
        self.body = ''
        self.body_chunks = []
        self.is_complete = False

    def feed(self, data):
        if self.is_complete:
            return

        nrecved = len(data)
        self.parser.execute(data, nrecved)

        if not self.parser.is_headers_complete():
            return

        if self.parser.is_partial_body():
            self.body_chunks.append(self.parser.recv_body())

        if (self.parser.get_method() != "POST"
            or self.parser.is_message_complete()):
            self.body = b''.join(self.body_chunks)
            self.is_complete = True

    def token(self):
        auth_header = self.parser.get_headers().get('authorization', None)
        if auth_header is not None:
            return auth_header.split()[1].strip()
        else:
            return None

    def is_websocket(self):
        # TODO: More elaborate check
        return 'websocket' in self.parser.get_headers().get('upgrade', '')


def websocket_response(request):
    websocket_key = request.parser.get_headers().get('Sec-WebSocket-Key')
    websocket_key = bytes(websocket_key, 'utf-8')
    sha = hashlib.sha1(websocket_key+WEBSOCKET_MAGIC_STRING)
    accept = base64.b64encode(sha.digest())
    return b'\r\n'.join([
        b'HTTP/1.1 101 Switching Protocols',
        b'Upgrade: websocket',
        b'Connection: Upgrade',
        b'Sec-WebSocket-Accept: ' + accept,
        b'',
        b''
    ])


def http_response(request, status=200):
    assert request is not None
    return b"HTTP Response"
