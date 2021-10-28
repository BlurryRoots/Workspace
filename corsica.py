#!/usr/bin/env python3
# encoding: utf-8
"""Minimalistic replacement for simple `python3 -m http.server` development servers when you need CORS or rewrite rules."""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import argparse
import os
import json
import urllib.parse
import re
from string import Template
import sys
import ssl


project_path = os.path.dirname(os.path.realpath(__file__))


def get_version():
    return '0.9.1'


_g_verbose = False
def _vprint(*c):
    if _g_verbose:
        print(*c)


class WorkingDirectory:
    """Context manager for changing the current working directory"""

    def __init__(self, context_path):
        self.context_path = os.path.expanduser(context_path)

    def __enter__(self):
        self.previous_path = os.getcwd()
        os.chdir(self.context_path)
        return self

    def __exit__(self, etype, value, traceback):
        os.chdir(self.previous_path)


class Corsica(SimpleHTTPRequestHandler):
    """Implementation of request handler to allow for rewrite rules and CORS.
    """

    def setup_configuration(self, configuration):
        """Reads rewrite rules from configuration"""
        self.rewrites = {}
        rewrites = configuration['rewrites'] \
            if 'rewrites' in configuration \
            else {}
        for k in rewrites.keys():
            t = Template(rewrites[k])
            r = re.compile(k)
            _vprint(f'Setting up rule({r.pattern}) with template({t.template}).')
            self.rewrites[r] = t

        self.allowed_origin = configuration['origin'] \
            if 'origin' in configuration \
            else '*'

        self.allowed_methods = []
        methods = configuration['methods'] \
            if 'methods' in configuration \
            else ['*']
        for m in methods:
            self.allowed_methods.append(m.upper())

        self.allowed_headers = []
        headers = configuration['headers'] \
            if 'headers' in configuration \
            else ['*']
        for h in headers:
            self.allowed_headers.append(h)

        self.cc = configuration['cache'] \
            if 'cache' in configuration \
            else ['no-store', 'no-cache', 'must-revalidate']

    def setup_server_path(self, server_path, execution_path):
        """Sets up exectution and server path"""
        self.server_path = server_path
        self.execution_path = execution_path

    def translate_path(self, path):
        """Override called when resource is requested and absolute path has to be constructed"""

        path_override = False
        # Changed relative path to rewrite rule if specified.
        for rule in self.rewrites:
            match = rule.match(path)
            if match:
                oldpath = path
                path = self.rewrites[rule].safe_substitute(match.groupdict())
                path_override = True
                _vprint(f'Translating: {oldpath} => {path}')
                break
        ur = self.server_path + path
        u = urllib.parse.urlparse(urllib.parse.unquote(ur))
        _vprint(f'{ur} => {u}')
        return u.path

    def end_headers(self):
        """Appends CORS headers to response."""

        # Where do we come from anyways?
        self.send_header('Access-Control-Allow-Origin', self.allowed_origin)
        # Your method of choice.
        self.send_header('Access-Control-Allow-Methods', ', '.join(self.allowed_methods))
        # Don't lose your head(er).
        self.send_header('Access-Control-Allow-Headers', ', '.join(self.allowed_headers))
        # Doin' some cachin', eh?!
        self.send_header('Cache-Control', ', '.join(self.cc))

        # Return full header collection.
        return super().end_headers()


def build_corsica_handler_class(configuration, server_path, execution_path):
    """Builds corsica http handler with custom config and paths."""

    class CorsicaArgumentWrapper(Corsica):
        def __init__(self, *args, **kwargs):
            _vprint('Initializing CorsicaArgumentWrapper ...')
            self.setup_configuration(configuration)
            self.setup_server_path(server_path, execution_path)
            super(CorsicaArgumentWrapper, self).__init__(*args, **kwargs)

    return CorsicaArgumentWrapper


def build_corsica_server_class(execution_path, server_path, server_address, configuration):
    _vprint(f'Generator function for corsica server class ...')
    handler_class = build_corsica_handler_class(configuration, server_path, execution_path)

    class CorsicaServer(HTTPServer):        
        """Corsica HTTP server, using custom HTTP handler and rewrite and path configuration."""
        def __init__(self):#(self, execution_path, server_path, server_address, configuration):
            self.base_path = server_path
            super(CorsicaServer, self).__init__(server_address, RequestHandlerClass=handler_class)

    return CorsicaServer


def run_host_command(args):
    # Change working directory context to configured server root.
    with WorkingDirectory(args.server_root) as cwd:
        # Construct configuration path relative or absolute and load.
        configuration = None
        if os.path.isabs(args.config):
            configuration_path = args.config
        else:
            configuration_path = os.path.join(cwd.previous_path, args.config)

        _vprint(f'Looking for a configuration file at {configuration_path} ...')

        if os.path.exists(configuration_path):
            with open(configuration_path, 'r') as cf:
                configuration = json.loads(cf.read())
        else:
            _vprint(f'No configuration file found. Setting up defaults ...')
            configuration = {}

        # Build server location info (hostname, port).
        location = (args.host, args.port)
        print(f"Hosting directory ({os.getcwd()}) via: {location}")

        # Start corsica server.
        CorsicaServer = build_corsica_server_class(cwd.previous_path, os.getcwd(), location, configuration)
        httpd = CorsicaServer()

        if args.ssl:
            _vprint(f'Setting up ssl. Looking for key at {args.key_file} and certificate at {args.cert_file}')
            httpd.socket = ssl.wrap_socket (httpd.socket, 
                certfile=args.cert_file, keyfile=args.key_file, server_side=True)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt as ki:
            sys.exit(1)

    return 0


def main():
    """Main entry point of command line tool."""

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose'
        , action='store_true'
        , help='Activate verbose logging.'
        , default=False)
    parser.add_argument('-V', '--version'
        , action='store_true'
        , help='Show version number.'
        , default=False)
    parser.add_argument('server_root', metavar='root'
        , type=str
        , help='Server root directory.')
    parser.add_argument('--port',
        metavar='port', type=int, help='Port to host on.', default=8080)
    parser.add_argument('--host', metavar='host', type=str
        , default='localhost'
        , help='Hostname.')
    parser.add_argument('--config',  metavar='config'
        , type=str, default='./corsica.conf'
        , help='Path to configuration file.')
    parser.add_argument('-S', '--ssl'
        , action='store_true'
        , help='Use SSL / HTTPS.'
        , default=False)
    parser.add_argument('--cert-file', metavar='cert_file'
        , type=str, default=os.path.join(project_path, 'corsica-cert.pem')
        , help='Path to ssl pem file. (default: corsica dev cert)')
    parser.add_argument('--key-file', metavar='key_file'
        , type=str, default=os.path.join(project_path, 'corsica-key.pem')
        , help='Path to ssl key file. (default: corsica dev key)')

    args = parser.parse_args()
    
    command = 'host'
    status = 0

    global _g_verbose
    _g_verbose = args.verbose

    if args.version:
        print(get_version())
        sys.exit(status)

    commands = {
        'host': run_host_command
    }

    if not command in commands:
        parser.print_help()
        status = 1
    else:
        status = commands[command](args)

    sys.exit(status)


if __name__ == '__main__':
    """Entry point when script is executed."""
    main()