import socket
import unittest

from api_control_block import check_port, require_streaming


class PortOwnershipTests(unittest.TestCase):
    def test_streaming_requires_observed_mode(self):
        for value in (None, 0, -1, '20480', True):
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'unsupported'):
                require_streaming({'engine': {'kv_resident': value}})
        require_streaming({'engine': {'kv_resident': 20480}})

    def test_active_listener_is_never_adopted(self):
        with socket.socket() as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', 0))
            server.listen()
            with self.assertRaises(OSError):
                check_port(server.getsockname()[1])

    def test_recent_closed_connection_does_not_block_next_process(self):
        with socket.socket() as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', 0))
            port = server.getsockname()[1]
            server.listen()
            with socket.create_connection(('127.0.0.1', port)) as client:
                connection, _ = server.accept()
                connection.close()  # server enters TIME_WAIT after client closes
                self.assertEqual(client.recv(1), b'')
        check_port(port)
