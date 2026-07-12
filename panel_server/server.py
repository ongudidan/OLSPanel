#!/usr/bin/env python3
import os
import sys
import ssl
import socket
import select
import threading
import argparse
import socketserver
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

# Define default paths (based on OLSPanel structure)
SYSTEM_PY_LIBS = [
    '/usr/lib/python3.12',
    '/usr/lib/python3.12/lib-dynload',
    '/root/venv/lib/python3.12/site-packages'
]
for path in SYSTEM_PY_LIBS:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

BASE_DIR = '/usr/local/olspanel/mypanel'
sys.path.append(BASE_DIR)

class ThreadedWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    """Multi-threaded WSGI server to handle concurrent requests and long-running connections."""
    daemon_threads = True
    allow_reuse_address = True

class PanelWSGIRequestHandler(WSGIRequestHandler):
    """Custom request handler that intercepts WebSockets and tunnels them to backend PHP socket."""
    
    def get_environ(self):
        environ = super().get_environ()
        environ['wsgi.url_scheme'] = 'https'
        environ['HTTPS'] = 'on'
        environ['HTTP_X_FORWARDED_PROTO'] = 'https'
        return environ
    
    def handle_one_request(self):
        """Intercepts WebSocket upgrade requests before passing to the standard WSGI flow."""
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(414)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not self.parse_request():
                return

            # Check for WebSocket Upgrade headers
            connection_hdr = self.headers.get('Connection', '').lower()
            upgrade_hdr = self.headers.get('Upgrade', '').lower()
            
            is_websocket = 'websocket' in upgrade_hdr or 'upgrade' in connection_hdr and 'websocket' in upgrade_hdr

            if is_websocket:
                self.handle_websocket_tunnel()
            else:
                # Standard HTTP request: Handover to WSGI handler
                super().handle_one_request()
        except socket.timeout as e:
            self.log_error("Request timed out: %r", e)
            self.close_connection = True
            return
        except Exception as e:
            self.log_error("Error handling request: %r", e)
            self.close_connection = True
            return

    def handle_websocket_tunnel(self):
        """Tunnels the WebSocket handshake and subsequent frames between client and local PHP backend."""
        backend_host = '127.0.0.1'
        backend_port = 9090
        
        self.log_message("WebSocket upgrade requested for path: %s. Tunneling to backend on %s:%d", 
                         self.path, backend_host, backend_port)

        try:
            backend_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_sock.settimeout(10.0)
            backend_sock.connect((backend_host, backend_port))
            backend_sock.settimeout(None) # Set back to blocking mode for tunnel
        except Exception as e:
            self.log_error("Failed to connect to backend WebSocket server: %s", str(e))
            self.send_error(502, f"Bad Gateway: Backend connection failed: {e}")
            return

        # Re-construct the initial request line and headers to send to backend
        req_lines = [f"{self.command} {self.path} {self.request_version}"]
        for header, val in self.headers.items():
            req_lines.append(f"{header}: {val}")
        req_raw = "\r\n".join(req_lines) + "\r\n\r\n"

        try:
            backend_sock.sendall(req_raw.encode('utf-8'))
        except Exception as e:
            self.log_error("Failed to forward headers to backend: %s", str(e))
            backend_sock.close()
            self.send_error(502, "Bad Gateway: Forwarding headers failed")
            return

        # Start bi-directional data forwarding
        client_sock = self.connection
        
        def forward(src, dest, label_src, label_dest):
            try:
                while True:
                    data = src.recv(8192)
                    if not data:
                        break
                    dest.sendall(data)
            except Exception as ex:
                pass
            finally:
                try:
                    src.close()
                except Exception:
                    pass
                try:
                    dest.close()
                except Exception:
                    pass

        # Use daemon threads to handle raw byte copies
        t_to_backend = threading.Thread(target=forward, args=(client_sock, backend_sock, "client", "backend"))
        t_to_client = threading.Thread(target=forward, args=(backend_sock, client_sock, "backend", "client"))
        t_to_backend.daemon = True
        t_to_client.daemon = True
        
        t_to_backend.start()
        t_to_client.start()

        # Prevent the handler from closing the socket or trying to parse further HTTP requests
        self.close_connection = True

def main():
    # Read default port dynamically from /etc/olspanel/port if available
    default_port = 6656
    port_file = '/etc/olspanel/port'
    if os.path.exists(port_file):
        try:
            with open(port_file, 'r') as f:
                content = f.read().strip()
                if content.isdigit():
                    default_port = int(content)
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Custom OLSPanel SSL/WS Web Server Wrapper")
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=default_port, help='Port to run the panel on')
    parser.add_argument('--test', action='store_true', help='Validate imports and configurations, then exit')
    args = parser.parse_args()

    # Load Django environment
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'user_management.settings')
        import django
        django.setup()
        from user_management.wsgi import application
    except Exception as e:
        print(f"❌ Failed to load Django WSGI application: {e}")
        sys.exit(1)

    if args.test:
        print("✅ Django WSGI application loaded successfully.")
        sys.exit(0)

    # Locate SSL files
    cert_path = os.path.join(BASE_DIR, 'cert.pem')
    key_path = os.path.join(BASE_DIR, 'key.pem')

    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print(f"❌ SSL Certificate files not found at:\nCert: {cert_path}\nKey: {key_path}")
        sys.exit(1)

    print(f"🚀 Starting Threaded OLSPanel HTTPS Server on https://{args.host}:{args.port}")
    
    # Initialize the server
    try:
        httpd = ThreadedWSGIServer((args.host, args.port), PanelWSGIRequestHandler)
        httpd.set_app(application)

        # Apply SSL/TLS Wrapper
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
        
        print("🔒 SSL Context loaded and bound successfully.")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"❌ Server crash: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
