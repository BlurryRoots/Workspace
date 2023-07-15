#!/usr/bin/env python3
# encoding: utf-8
"""
Minimalistic replacement for simple `python3 -m http.server` development servers
when you need CORS or rewrite rules.

Copyright (c) blurryroots innovation qanat OÜ
"""
from http.server import HTTPServer, BaseHTTPRequestHandler #SimpleHTTPRequestHandler
import argparse
import os
import json
import urllib.parse
import re
from string import Template
import sys
import ssl
import datetime
import cgi
import traceback

import copy
import datetime
import email.utils
import html
import http.client
import io
import mimetypes
import os
import posixpath
import select
import shutil
import socket # For gethostbyaddr()
import socketserver
import sys
import time
import urllib.parse

from http import HTTPStatus


project_path = os.path.dirname(os.path.realpath(__file__))


def get_favicon ():
    data = io.StringIO()
    data.write (FAVICON_STATID_BASE64)
    return data


def get_version():
    return '0.9.1'


class SimpleHTTPRequestHandlerStream(BaseHTTPRequestHandler):

    """Simple HTTP request handler with GET and HEAD commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method.

    The GET and HEAD requests are identical except that the HEAD
    request omits the actual contents of the file.

    """

    server_version = "SimpleHTTP@Corsica/" + get_version()
    extensions_map = _encodings_map_default = {
        '.gz': 'application/gzip',
        '.Z': 'application/octet-stream',
        '.bz2': 'application/x-bzip2',
        '.xz': 'application/x-xz',
    }

    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = os.getcwd()
        self.directory = os.fspath(directory)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        # check for trailing "/" which should return 404. See Issue17324
        # The test for this was added in test_httpserver.py
        # However, some OS platforms accept a trailingSlash as a filename
        # See discussion on python-dev and Issue34711 regarding
        # parseing and rejection of filenames with a trailing slash
        if path.endswith("/"):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            # Use browser cache if possible
            if ("If-Modified-Since" in self.headers
                    and "If-None-Match" not in self.headers):
                # compare If-Modified-Since and time of last file modification
                try:
                    ims = email.utils.parsedate_to_datetime(
                        self.headers["If-Modified-Since"])
                except (TypeError, IndexError, OverflowError, ValueError):
                    # ignore ill-formed values
                    pass
                else:
                    if ims.tzinfo is None:
                        # obsolete format with no timezone, cf.
                        # https://tools.ietf.org/html/rfc7231#section-7.1.1.1
                        ims = ims.replace(tzinfo=datetime.timezone.utc)
                    if ims.tzinfo is datetime.timezone.utc:
                        # compare to UTC datetime of last modification
                        last_modif = datetime.datetime.fromtimestamp(
                            fs.st_mtime, datetime.timezone.utc)
                        # remove microseconds, like in If-Modified-Since
                        last_modif = last_modif.replace(microsecond=0)

                        if last_modif <= ims:
                            self.send_response(HTTPStatus.NOT_MODIFIED)
                            self.end_headers()
                            f.close()
                            return None

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified",
                self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except OSError:
            self.send_error(
                HTTPStatus.NOT_FOUND,
                "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        r = []
        try:
            displaypath = urllib.parse.unquote(self.path,
                                               errors='surrogatepass')
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(path)
        displaypath = html.escape(displaypath, quote=False)
        enc = sys.getfilesystemencoding()
        title = 'Directory listing for %s' % displaypath
        r.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                 '"http://www.w3.org/TR/html4/strict.dtd">')
        r.append('<html>\n<head>')
        r.append('<meta http-equiv="Content-Type" '
                 'content="text/html; charset=%s">' % enc)
        r.append('<title>%s</title>\n</head>' % title)
        r.append('<body>\n<h1>%s</h1>' % title)
        r.append('<hr>\n<ul>')
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            r.append('<li><a href="%s">%s</a></li>'
                    % (urllib.parse.quote(linkname,
                                          errors='surrogatepass'),
                       html.escape(displayname, quote=False)))
        r.append('</ul>\n<hr>\n</body>\n</html>\n')
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "text/html; charset=%s" % enc)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        # Don't forget explicit trailing slash when normalizing. Issue17324
        trailing_slash = path.rstrip().endswith('/')
        try:
            path = urllib.parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        path = self.directory
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                # Ignore components that are not a simple file/directory name
                continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += '/'
        return path

    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile, length = 256*1024)

    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """
        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        guess, _ = mimetypes.guess_type(path)
        if guess:
            return guess
        return 'application/octet-stream'


def rfc8601 ():
    d = datetime.datetime.now ().strftime ("%Y%m%dT%H%M%S.%fZ")
    return d


_g_verbose = False
def _vprint(*c):
    if _g_verbose:
        sys.stderr.write(f'[{rfc8601 ()}](V) ')
        sys.stderr.write(*c)
        sys.stderr.write('\n')
        sys.stderr.flush ()


def _print(*c):
    sys.stdout.write(f'[{rfc8601 ()}] ')
    sys.stdout.write(*c)
    sys.stdout.write('\n')
    sys.stdout.flush ()


class WorkingDirectory:
    """Context manager for changing the current working directory"""

    def __init__(self, context_path):
        _vprint(f'Initializing WorkingDirectory for "{context_path}"')
        self.context_path = os.path.expanduser(context_path)

    def __enter__(self):
        _vprint(f'Entering WorkingDirectory ...')
        self.previous_path = os.getcwd()
        os.chdir(self.context_path)
        return self

    def __exit__(self, etype, value, traceback):
        _vprint(f'Exiting WorkingDirectory ...')
        os.chdir(self.previous_path)


class Corsica(SimpleHTTPRequestHandlerStream):
    """Implementation of request handler to allow for rewrite rules and CORS.
    """

    def setup_configuration(self, configuration):
        """Reads rewrite rules from configuration"""
        _vprint('Setting up configuration ...')
        self.rewrites = {}
        rewrites = configuration['rewrites'] \
            if 'rewrites' in configuration \
            else {}
        for k in rewrites.keys():
            t = Template(rewrites[k])
            r = re.compile(k)
            _vprint(f'Setting up rule({r.pattern}) with template({t.template}).')
            self.rewrites[r] = t

        #if not '/favicon.ico' in self.rewrites:
        #    self.rewrites[re.compile('/favicon.ico')] = Template(os.path.join (project_path, 'favicon.ico'))

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
        _vprint('Setting up paths ...')
        self.server_path = server_path
        _vprint(f'server_path: {self.server_path}')
        self.execution_path = execution_path
        _vprint(f'execution_path: {self.execution_path}')

    def translate_path(self, path):
        """Override called when resource is requested and absolute path has to be constructed"""
        _vprint(f'Translating path "{path}" ...')
        path_override = False
        # Changed relative path to rewrite rule if specified.
        for rule in self.rewrites:
            match = rule.match(path)
            if match:
                oldpath = path
                path = self.rewrites[rule].safe_substitute(match.groupdict())
                path_override = True
                _vprint(f'Applying rule[{rule}]: {oldpath} => {path}')
                break
        #ur = path.replace('/', '', 1) if path.startswith ('/') else path
        #_vprint (f'Does {ur} exist?')
        #if not os.path.exists (ur):
        #    _vprint (f'Prepend server path.')
        #    ur = os.path.join (self.server_path, ur)
        #
        relative_path = path.replace('/', '', 1) if path.startswith ('/') else path
        _vprint(f'How?')
        _vprint(f'self.server_path: {self.server_path}')
        _vprint(f'path: {relative_path}')
        ur = os.path.join(self.server_path, relative_path)
        _vprint(f'ur: {ur}')
        _vprint(f'Building file path from "{relative_path}" to {ur} (server_path: {self.server_path}) ...')
        u = urllib.parse.urlparse(urllib.parse.unquote(ur))

        _vprint(f'{ur} => {u}')
        return u.path

    def end_headers(self):
        """Appends CORS headers to response."""
        _vprint(f'Appending CORS headers ...')

        # Remove default server header entry.
        server_header_i = -1
        for i in range (0, len (self._headers_buffer)):
            if b'Server: ' in self._headers_buffer[i]:
                server_header_i = i
        if -1 < server_header_i:
            del self._headers_buffer[server_header_i]

        # Who's this?
        self.send_header('Server', f'Corsica {get_version ()}')
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

    def do_POST(self):
        _print ('Handling upload ...')
        k = {}
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                         'CONTENT_TYPE':self.headers['Content-Type'],
                         })
            upload_dir = os.path.join (os.getcwd(), '_upload')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            if not 'file' in form:
                raise Exception ('Form data is missing field! (file)')
            file_name = os.path.join (upload_dir, form['file'].filename)
            file_length = int(self.headers['Content-Length'])
            #file_content = self.rfile.read(file_length)
            file_content = form['file'].file.read()


            _print (f'Writing file to "{file_name}" ...')
            with open (file_name, 'wb') as f:
                f.write (file_content)

            k['time'] = f'{rfc8601 ()}'
            k['r'] = 200
            k['filename'] = file_name
        except Exception as e:
            _print (f'Caught exception: "{e}"')
            traceback.print_exc()
            k['r'] = 400
        finally:
            self.send_response(k['r'])
            self.send_header("Content-type", "text/json")
            self.end_headers()
            retstr = json.dumps (k)
            _print (f'Sending: "{retstr}" ...')
            self.wfile.write (retstr.encode ('utf8'))


def build_corsica_handler_class(configuration, server_path, execution_path):
    """Builds corsica http handler with custom config and paths."""
    _vprint(f'Building CorsicaArgumentWrapper ...')
    class CorsicaArgumentWrapper(Corsica):
        def __init__(self, *args, **kwargs):
            _vprint('Initializing CorsicaArgumentWrapper ...')
            self.setup_configuration(configuration)
            self.setup_server_path(server_path, execution_path)
            super(CorsicaArgumentWrapper, self).__init__(*args, **kwargs)

    _vprint(f'Wrapper ready ...')
    return CorsicaArgumentWrapper


def build_corsica_server_class(execution_path, server_path, server_address, configuration):
    _vprint(f'Generator function for corsica server class ...')
    handler_class = build_corsica_handler_class(configuration, server_path, execution_path)

    class CorsicaServer(HTTPServer):        
        """Corsica HTTP server, using custom HTTP handler and rewrite and
           path configuration."""
        def __init__(self):
            _vprint('Initializing server ...')
            self.base_path = server_path
            super(CorsicaServer, self).__init__(server_address
                , RequestHandlerClass=handler_class
            )

    _vprint('Server class ready.')
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
        _print(f'Hosting directory ({os.getcwd()}) via: {location}')

        # Start corsica server.
        CorsicaServer = build_corsica_server_class(cwd.previous_path
            , os.getcwd(), location, configuration
        )
        _vprint('Creating CorsicaServer ...')
        httpd = CorsicaServer()

        if args.ssl:
            _vprint(f'Setting up ssl. Looking for key at {args.key_file}'
                    f' and certificate at {args.cert_file}'
            )
            context = ssl.SSLContext (ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain (args.cert_file, args.key_file)            
            #raw_socket = httpd.socket
            with context.wrap_socket (httpd.socket, server_side=True) as secure_socket:
                httpd.socket = secure_socket
                _vprint (f'Start serving securly ...')
                httpd.serve_forever ()


            #httpd.socket = ssl.wrap_socket (httpd.socket
            #, certfile = args.cert_file
            #, keyfile = args.key_file
            #, server_side = True
            #, ssl_version = ssl.PROTOCOL_TLSv1
            #)
            #_vprint (f'Start serving securly ...')
            #httpd.serve_forever ()

        else:
            _vprint (f'Start serving ...')
            httpd.serve_forever ()

    return 0


def main():
    """Main entry point of command line tool."""

    parser = argparse.ArgumentParser()
    parser.add_argument('server_root', metavar='root'
        , type=str
        , help='Server root directory.'
    )
    parser.add_argument('-v', '--verbose'
        , action='store_true'
        , help='Activate verbose logging.'
        , default=False
    )
    parser.add_argument('-V', '--version'
        , action='store_true'
        , help='Show version number.'
        , default=False
    )
    parser.add_argument('-p', '--port',
        metavar='port', type=int, help='Port to host on.', default=8080
    )
    parser.add_argument('-H', '--host', metavar='host', type=str
        , default='localhost'
        , help='Hostname.'
    )
    parser.add_argument('--config',  metavar='config'
        , type=str, default='./corsica.conf'
        , help='Path to configuration file.'
    )
    parser.add_argument('-S', '--ssl'
        , action='store_true'
        , help='Use SSL / HTTPS.'
        , default=False
    )
    parser.add_argument('--cert-file', metavar='cert_file'
        , type=str, default=os.path.join(project_path, 'corsica-cert.pem')
        , help='Path to ssl pem file. (default: corsica dev cert)'
    )
    parser.add_argument('--key-file', metavar='key_file'
        , type=str, default=os.path.join(project_path, 'corsica-key.pem')
        , help='Path to ssl key file. (default: corsica dev key)'
    )

    args = parser.parse_args()
    
    command = 'host'
    status = 0

    global _g_verbose
    _g_verbose = args.verbose

    if args.version:
        print(get_version())
        return status

    commands = {
        'host': run_host_command
    }

    if not command in commands:
        parser.print_help()
        status = 1
    else:
        try:
            status = commands[command](args)
        except KeyboardInterrupt as ki:
            _print('Shutting down ...')

    return status


if __name__ == '__main__':
    """Entry point when script is executed."""
    sys.exit(main())

# ..