"""
Unit tests for pods-read-logs.py.

pods-read-logs.py has a hyphenated filename, so it is loaded with importlib. It does
"import common", which resolves through the inserted sys.path to a module object
distinct from contents.common, so patches target pods_read_logs.common.
"""

import importlib
import io
import os
import sys
import unittest

from contextlib import redirect_stdout
from unittest.mock import patch

from kubernetes.client.rest import ApiException


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

pods_read_logs = importlib.import_module('pods-read-logs')


def node_params(name='my-pod', namespace='default', container='app'):
    return {'name': name, 'namespace': namespace, 'container_name': container}

class TestPodsReadLogs(unittest.TestCase):

    def setUp(self):
        os.environ.clear()

    @patch.object(pods_read_logs.client, 'CoreV1Api')
    @patch.object(pods_read_logs.common, 'connect')
    @patch.object(pods_read_logs.common, 'get_code_node_parameter_dictionary')
    def test_main_reads_logs_for_named_container(
            self, mock_params, mock_connect, mock_api_class):
        mock_params.return_value = node_params()
        mock_api_class.return_value.read_namespaced_pod_log.return_value.read.return_value = b'line'

        with redirect_stdout(io.StringIO()):
            pods_read_logs.main()

        kwargs = mock_api_class.return_value.read_namespaced_pod_log.call_args[1]
        self.assertEqual('my-pod', kwargs['name'])
        self.assertEqual('default', kwargs['namespace'])
        self.assertEqual('app', kwargs['container'])

    @patch.object(pods_read_logs.client, 'CoreV1Api')
    @patch.object(pods_read_logs.common, 'connect')
    @patch.object(pods_read_logs.common, 'get_code_node_parameter_dictionary')
    def test_main_reads_logs_without_a_container(
            self, mock_params, mock_connect, mock_api_class):
        mock_params.return_value = node_params(container=None)
        mock_api_class.return_value.read_namespaced_pod_log.return_value.read.return_value = b'line'

        with redirect_stdout(io.StringIO()):
            pods_read_logs.main()

        kwargs = mock_api_class.return_value.read_namespaced_pod_log.call_args[1]
        self.assertNotIn('container', kwargs)

    @patch.object(pods_read_logs.client, 'CoreV1Api')
    @patch.object(pods_read_logs.common, 'connect')
    @patch.object(pods_read_logs.common, 'get_code_node_parameter_dictionary')
    def test_main_decodes_log_bytes_rather_than_printing_a_repr(
            self, mock_params, mock_connect, mock_api_class):
        mock_params.return_value = node_params()
        mock_api_class.return_value.read_namespaced_pod_log.return_value.read.return_value = b'hello'

        out = io.StringIO()
        with redirect_stdout(out):
            pods_read_logs.main()

        self.assertIn('hello', out.getvalue())
        self.assertNotIn("b'hello'", out.getvalue())

    @patch('kubernetes.watch.Watch')
    @patch.object(pods_read_logs.client, 'CoreV1Api')
    @patch.object(pods_read_logs.common, 'connect')
    @patch.object(pods_read_logs.common, 'get_code_node_parameter_dictionary')
    def test_main_actually_follows_when_follow_is_requested(
            self, mock_params, mock_connect, mock_api_class, mock_watch):
        os.environ['RD_CONFIG_FOLLOW'] = 'true'
        mock_params.return_value = node_params()
        mock_watch.return_value.stream.return_value = ['line one']

        out = io.StringIO()
        with redirect_stdout(out):
            pods_read_logs.main()

        kwargs = mock_watch.return_value.stream.call_args[1]
        self.assertTrue(kwargs['follow'])
        self.assertEqual('app', kwargs['container'])
        self.assertIn('line one', out.getvalue())

    @patch.object(pods_read_logs.common, 'connect')
    @patch.object(pods_read_logs.common, 'get_code_node_parameter_dictionary')
    def test_main_exits_on_non_numeric_tail_lines(self, mock_params, mock_connect):
        os.environ['RD_CONFIG_NUMBER_OF_LINES'] = 'lots'
        mock_params.return_value = node_params()

        with self.assertRaises(SystemExit) as cm:
            pods_read_logs.main()
        self.assertEqual(1, cm.exception.code)

    @patch.object(pods_read_logs.client, 'CoreV1Api')
    @patch.object(pods_read_logs.common, 'connect')
    @patch.object(pods_read_logs.common, 'get_code_node_parameter_dictionary')
    def test_main_survives_non_utf8_container_output(
            self, mock_params, mock_connect, mock_api_class):
        # A UnicodeDecodeError is not an ApiException, so it would escape the
        # try as an unhandled traceback and show the operator no logs at all.
        mock_params.return_value = node_params()
        mock_api_class.return_value.read_namespaced_pod_log.return_value.read.return_value = (
            b'before \xff\xfe after')

        out = io.StringIO()
        with redirect_stdout(out):
            pods_read_logs.main()

        self.assertIn('before', out.getvalue())
        self.assertIn('after', out.getvalue())

    @patch.object(pods_read_logs.client, 'CoreV1Api')
    @patch.object(pods_read_logs.common, 'connect')
    @patch.object(pods_read_logs.common, 'get_code_node_parameter_dictionary')
    def test_main_exits_on_api_exception(self, mock_params, mock_connect, mock_api_class):
        mock_params.return_value = node_params()
        mock_api_class.return_value.read_namespaced_pod_log.side_effect = ApiException(
            status=404, reason='Not Found')

        with self.assertRaises(SystemExit) as cm:
            pods_read_logs.main()
        self.assertEqual(1, cm.exception.code)


if __name__ == '__main__':
    unittest.main()
