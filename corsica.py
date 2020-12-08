#!/usr/bin/env python3
# encoding: utf-8
"""Minimalistic replacement for simple `python3 -m http.server` development servers when you need CORS or rewrite rules."""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import argparse
import os
import json


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
        self.rewrites = configuration['rewrites'] if 'rewrites' in configuration else {}

    def setup_server_path(self, server_path, execution_path):
        """Sets up exectution and server path"""
        self.server_path = server_path
        self.execution_path = execution_path

    def translate_path(self, path):
        """Override called when resource is requested and absolute path has to be constructed"""

        # creates absulte path to requested resource
        #path = super(Corsica, self).translate_path(path)

        # Changed relative path to rewrite rule if specified.
        if path in self.rewrites:
            print(f'Found rewrite {path} => {self.rewrites[path]}')
            path = self.rewrites[path]

        return self.server_path + path

    def end_headers(self):
        """Appends CORS headers to response."""

        # Allow CORS from all origins.
        self.send_header('Access-Control-Allow-Origin', '*')
        # For GET method.
        self.send_header('Access-Control-Allow-Methods', 'GET')
        # And disable caching.
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')

        # Return full header collection.
        return super().end_headers()


def build_corsica_handler_class(configuration, server_path, execution_path):
    """Builds corsica http handler with custom config and paths."""

    class CorsicaArgumentWrapper(Corsica):
        def __init__(self, *args, **kwargs):
            self.setup_configuration(configuration)
            self.setup_server_path(server_path, execution_path)
            super(CorsicaArgumentWrapper, self).__init__(*args, **kwargs)
    return CorsicaArgumentWrapper


class CorsicaServer(HTTPServer):
    """Corsica HTTP server, using custom HTTP handler and rewrite and path configuration."""
    def __init__(self, execution_path, server_path, server_address, configuration):
        self.base_path = server_path
        handler_class = build_corsica_handler_class(configuration, server_path, execution_path)
        super(CorsicaServer, self).__init__(server_address, RequestHandlerClass=handler_class)


def main():
    """Main entry point of command line tool."""

    parser = argparse.ArgumentParser()
    parser.add_argument('server_root',
        metavar='root', type=str, help='Server root directory.')
    parser.add_argument('--port',
        metavar='port', type=int, help='Port to host on.', default=8080)
    parser.add_argument('--host',
        metavar='host', type=str, help='Hostname.', default='localhost')
    parser.add_argument('--config',
        metavar='config', type=str, help='Path to configuration file.', default='./corsica.conf')

    args = parser.parse_args()

    # Change working directory context to configured server root.
    with WorkingDirectory(args.server_root) as cwd:
        # Construct configuration path relative or absolute and load.
        configuration = None
        if os.path.isabs(args.config):
            configuration_path = args.config
        else:
            configuration_path = os.path.join(cwd.previous_path, args.config)

        with open(configuration_path, 'r') as cf:
            configuration = json.loads(cf.read())

        # Build server location info (hostname, port).
        location = (args.host, args.port)
        print(f"Hosting directory ({os.getcwd()}) server at: {location}")

        # Start corsica server.
        httpd = CorsicaServer(cwd.previous_path, os.getcwd(), location, configuration)
        httpd.serve_forever()


if __name__ == '__main__':
    """Entry point when script is executed."""
    main()