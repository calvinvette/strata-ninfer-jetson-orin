import socket
import unittest

from api_control_block import (check_port, configure_trace_environment,
                               require_streaming)


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


class ApiControlBlockTests(unittest.TestCase):
    def test_no_trace_removes_configured_and_inherited_trace_flags(self):
        config = {
            'STRATA_TRACE': '1',
            'STRATA_STATE_HASH': '1',
            'STRATA_INTEGRATION_TRACE': '1',
            'APP_SETTING': 'kept',
        }
        inherited = {
            'STRATA_TRACE': '1',
            'STRATA_STATE_HASH_GDN': '1',
            'STRATA_ACCEPTED_PREFIX_TRACE': '1',
            'PATH': '/bin',
        }

        result_config, result_env = configure_trace_environment(config, inherited, True)

        for key in ('STRATA_TRACE', 'STRATA_STATE_HASH', 'STRATA_STATE_HASH_GDN',
                    'STRATA_INTEGRATION_TRACE', 'STRATA_ACCEPTED_PREFIX_TRACE'):
            self.assertNotIn(key, result_config)
            self.assertNotIn(key, result_env)
        self.assertEqual(result_config['APP_SETTING'], 'kept')
        self.assertEqual(result_env['PATH'], '/bin')

    def test_normal_trace_mode_forces_strata_trace(self):
        result_config, result_env = configure_trace_environment({}, {'PATH': '/bin'}, False)
        self.assertEqual(result_config['STRATA_TRACE'], '1')
        self.assertEqual(result_env['STRATA_TRACE'], '1')
        self.assertEqual(result_env['PATH'], '/bin')


if __name__ == '__main__':
    unittest.main()
