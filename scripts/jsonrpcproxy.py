#!/usr/bin/env python3

"""
JSON-RPC Proxy

This Python script provides HTTP proxy to Unix Socket based JSON-RPC servers.
Check out --help option for more information.

Build with cython:

cython rpcproxy.py --embed
gcc -O3 -I /usr/include/python3.5m -o rpcproxy rpcproxy.c \
-Wl,-Bstatic -lpython3.5m -lz -lexpat -lutil -Wl,-Bdynamic -lpthread -ldl -lm

"""

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from http.server import HTTPServer, BaseHTTPRequestHandler
from os import path
from urllib.parse import urlparse
import socket


VERSION = '0.1.0a1'
BUFSIZE = 32
DELIMITER = ord('\n')
INFO = """JSON-RPC Proxy

Version: {}
Proxy: {}
Backend: {}
"""


class HTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        backend_url = 'unix:' + self.server.backend_address
        proxy_url = '{}:{}'.format(self.server.server_name,
                                   self.server.server_port)
        info = INFO.format(VERSION, backend_url, proxy_url)
        self.wfile.write(info.encode('utf-8'))

    def do_POST(self):
        request_length = int(self.headers['Content-Length'])
        request_content = self.rfile.read(request_length)
        # self.log_message("Headers:  {}".format(self.headers))
        self.log_message("Request:  {}".format(request_content))

        response_content = self.server.process(request_content)
        self.log_message("Response: {}".format(response_content))

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-length", len(response_content))
        self.end_headers()
        self.wfile.write(response_content)


class Proxy(HTTPServer):

    def __init__(self, proxy_url, backend_url):

        proxy_url = urlparse(proxy_url)
        assert proxy_url.scheme == 'http'
        proxy_address = proxy_url.hostname, proxy_url.port

        backend_url = urlparse(backend_url)
        assert backend_url.scheme == 'unix'

        super(Proxy, self).__init__(proxy_address, HTTPRequestHandler)

        self.backend_address = path.expanduser(backend_url.path)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.backend_address)

    def process(self, request):
        self.sock.sendall(request)

        response = b''
        while True:
            r = self.sock.recv(BUFSIZE)
            if not r:
                break
            if r[-1] == DELIMITER:
                response += r[:-1]
                break
            response += r

        return response


def run():
    parser = ArgumentParser(
        description='HTTP Proxy for JSON-RPC servers',
        formatter_class=ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('backend_url', nargs='?',
                        default='unix:~/.ethereum/geth.ipc',
                        help="URL to a backend RPC sever")
    parser.add_argument('proxy_url', nargs='?',
                        default='http://127.0.0.1:8545',
                        help="URL for this proxy server")
    args = parser.parse_args()
    proxy = Proxy(args.proxy_url, args.backend_url)
    proxy.serve_forever()


if __name__ == '__main__':
    run()
