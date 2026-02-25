import ssl

def create_ssl_context(certfile, keyfile):
    # Initializes the security context using modern TLS protocols
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # Loads your server.crt and server.key files to authenticate the server
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context

def wrap_socket(context, client_socket):
    # Wraps the plain TCP socket in an SSL layer for secure communication
    return context.wrap_socket(client_socket, server_side=True)
