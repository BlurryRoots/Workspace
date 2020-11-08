#!/usr/bin/env python3
# encoding: utf-8
"""Use instead of `python3 -m http.server` when you need CORS"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import argparse
import os

class DirectoryContext:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

class Corsica(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')

        return super().end_headers()

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action="store_true", default = False)

    parser.add_argument('server_root',
        metavar='R', type=str, help='Server root directory.')

    parser.add_argument('--port',
        metavar='P', type=int, help='Port to host on.', default=8080)

    args = parser.parse_args()

    if args.version:
        print(self.VERSION)
        return 0

    with DirectoryContext(args.server_root):
        location = ('localhost', args.port)
        print(f"Hosting directory ({os.getcwd()}) server at: {location}")
        httpd = HTTPServer(location, Corsica)
        httpd.serve_forever()

if __name__ == '__main__':
    main()