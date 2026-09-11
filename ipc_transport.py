"""Display-independent local command transport."""
import hashlib
import hmac
import socket

def get_or_create_ipc_token():
    # Installer command clients must not initialize application settings.
    from config_manager import get_or_create_ipc_token as obtain
    return obtain()

IPC_PORT = 49382


def reserve_listener():
    """Exclusive ownership is acquired synchronously before display imports."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(('127.0.0.1', IPC_PORT))
        listener.listen(5)
        listener.settimeout(1.0)
        return listener
    except BaseException:
        listener.close()
        raise


def ipc_ack(command, token):
    digest = hmac.new(token.encode('ascii'), command.encode('utf-8'), hashlib.sha256).hexdigest()[:32]
    return f'OK:{digest}'.encode('ascii')


import json
import secrets
import time


def _proof(token, direction, client_nonce, server_nonce, command=''):
    message = json.dumps(['night-light-ipc-v2', direction, client_nonce, server_nonce, command], separators=(',', ':'))
    return hmac.new(token.encode('ascii'), message.encode('utf-8'), hashlib.sha256).hexdigest()


def _send(conn, value):
    conn.sendall(json.dumps(value, separators=(',', ':')).encode('ascii') + b'\n')


def _receive(conn):
    # A complete frame has a bounded size AND wall-clock deadline.
    data = bytearray()
    deadline = time.monotonic() + 2.0
    while len(data) < 2048:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('IPC frame deadline')
        conn.settimeout(remaining)
        char = conn.recv(1)
        if not char:
            raise ValueError('Incomplete IPC frame')
        if char == b'\n':
            value = json.loads(data)
            if not isinstance(value, dict):
                raise ValueError('Invalid IPC frame')
            return value
        data.extend(char)
    raise ValueError('Oversize IPC frame')


def _nonce(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Invalid nonce')
    return value


def authenticate_request(conn, token):
    """Mutual proof; no reusable credential crosses the socket.

    Fresh nonces per connection and direction/command-bound HMACs prevent
    replay and reflection. Legacy bearer requests intentionally fail closed.
    """
    hello = _receive(conn)
    client_nonce = _nonce(hello.get('hello'))
    server_nonce = secrets.token_hex(32)
    _send(conn, {'nonce': server_nonce, 'proof': _proof(token, 'server', client_nonce, server_nonce)})
    request = _receive(conn)
    command = request.get('command')
    proof = request.get('proof')
    if not isinstance(command, str) or not command or len(command) > 128:
        raise ValueError('Invalid command')
    if not isinstance(proof, str) or not proof.isascii() or not hmac.compare_digest(proof, _proof(token, 'client', client_nonce, server_nonce, command)):
        raise ValueError('Invalid client proof')
    return command, (client_nonce, server_nonce)


def acknowledge(conn, token, command, nonces, handled):
    _send(conn, {'proof': _proof(token, 'ack', *nonces, command) if handled else ''})


def send_ipc_command(command='TOGGLE', *, existing_token=None):
    try:
        token = get_or_create_ipc_token() if existing_token is None else existing_token
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(2.0)
            client.connect(('127.0.0.1', IPC_PORT))
            client_nonce = secrets.token_hex(32)
            _send(client, {'hello': client_nonce})
            challenge = _receive(client)
            server_nonce = _nonce(challenge.get('nonce'))
            proof = challenge.get('proof', '')
            if not isinstance(proof, str) or not proof.isascii() or not hmac.compare_digest(proof, _proof(token, 'server', client_nonce, server_nonce)):
                return False
            _send(client, {'command': command, 'proof': _proof(token, 'client', client_nonce, server_nonce, command)})
            reply = _receive(client).get('proof', '')
            return isinstance(reply, str) and reply.isascii() and hmac.compare_digest(reply, _proof(token, 'ack', client_nonce, server_nonce, command))
    except (OSError, ValueError, TypeError, UnicodeError):
        return False


def request_resident_exit():
    """Authenticate to an existing resident only; never create/repair settings.

    True means request acknowledged, not proof the process or file locks exited.
    Installer must independently wait for that evidence before changing files.
    """
    from config_paths import config_directory
    try:
        path=config_directory()/'config.json'
        if path.is_symlink():return False
        with path.open('rb') as stream:raw=stream.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:return False
        data=json.loads(raw)
        token=data.get('ipc_token')
        if not isinstance(token,str) or not 32<=len(token)<=256 or not token.isascii():return False
        return send_ipc_command('QUIT',existing_token=token)
    except (OSError,ValueError,TypeError,AttributeError):
        return False
