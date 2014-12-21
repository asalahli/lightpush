import re


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


class HttpResponse(object):
    def __init__(self, status=200):
        self.status = status
        self.headers = {}

    def __str__(self):
        header = [
            'HTTP/1.1 {0} {1}'.format(self.status, messages[self.status])
        ]
        for key, value in self.headers.iteritems():
            header.append(key + ': ' + value)
        return '\r\n'.join(header)