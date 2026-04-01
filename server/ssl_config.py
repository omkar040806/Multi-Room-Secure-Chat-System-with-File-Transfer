# server/ssl_config.py
import ssl


def create_ssl_context(certfile: str, keyfile: str) -> ssl.SSLContext:
    """
    Build a hardened TLS 1.3-only server context.
    TLS 1.0 and 1.1 are explicitly disabled.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    # Force TLS 1.2 minimum; prefer 1.3 where available
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Disable weak ciphers
    context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!MD5:!RC4")

    return context


def wrap_socket(context: ssl.SSLContext, client_socket):
    """Wrap a plain TCP socket in TLS. Returns the secure socket."""
    return context.wrap_socket(client_socket, server_side=True)
