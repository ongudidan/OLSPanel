import os
import sys
from io import BytesIO

# Add project directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'user_management.settings')

try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    print("Django WSGI application loaded successfully.")
except Exception as e:
    print(f"Error loading Django WSGI application: {e}", file=sys.stderr)
    application = None
    
def _is_true(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)

def handle_request(environ, chunked=False):
    """
    Returns:
        status_line (string)
        headers_list (list of tuples)
        body_iter (iterator of bytes) if chunked=True, else full bytes
    """
    if application is None:
        body = b"Django application failed to load."
        return (
            "500 Internal Server Error",
            [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))],
            body
        )

    headers_set = []
    status_line = ""

    def write(data: bytes):
        # dummy write for WSGI
        pass

    def start_response(status, headers, exc_info=None):
        nonlocal headers_set, status_line
        status_line = status
        headers_set = headers
        return write

    result = application(environ, start_response)

    if _is_true(chunked):
        # Generator to yield chunks in real-time
        def chunk_generator():
            try:
                for data in result:
                    if isinstance(data, str):
                        data = data.encode("utf-8")
                    if data:
                        # yield chunk in proper hex + CRLF format
                        size = f"{len(data):X}\r\n".encode("utf-8")
                        yield size
                        yield data + b"\r\n"
                # end chunked
                yield b"0\r\n\r\n"
            finally:
                if hasattr(result, "close"):
                    result.close()

        # Keep Transfer-Encoding: chunked header
        filtered_headers = [(k, v) for k, v in headers_set if k.lower() not in ("content-length", "content-encoding")]
        filtered_headers.append(("Transfer-Encoding", "chunked"))

        return status_line, filtered_headers, chunk_generator()

    else:
        # normal full-body response
        body_bytes = b"".join(
            (d.encode("utf-8") if isinstance(d, str) else d) for d in result
        )
        if hasattr(result, "close"):
            result.close()

        # remove chunked/gzip headers and force content-length
        filtered_headers = [(k, v) for k, v in headers_set if k.lower() not in ("transfer-encoding", "content-encoding")]
        if not any(h[0].lower() == "content-length" for h in filtered_headers):
            filtered_headers.append(("Content-Length", str(len(body_bytes))))

        return status_line, filtered_headers, body_bytes