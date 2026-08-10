"""
Unit tests for pods-delete.py.

pods-delete.py has a hyphenated filename, so it is loaded with importlib. It does
"import common", which resolves through the inserted sys.path to a module object
distinct from contents.common, so patches target pods_delete.common.
"""

import importlib
import io
import os
import sys
import unittest

from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from kubernetes.client.rest import ApiException


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

pods_delete = importlib.import_module('pods-delete')


def node_params(name='my-pod', namespace='default', container='app'):
    return {'name': name, 'namespace': namespace, 'container_name': container}

class TestPodsDelete(unittest.TestCase):

    def setUp(self):
        os.environ.clear()

    @patch.object(pods_delete.common, 'delete_pod')
    @patch.object(pods_delete.common, 'connect')
    @patch.object(pods_delete.common, 'get_code_node_parameter_dictionary')
    def test_main_reports_success_when_delete_returns_a_response(
            self, mock_params, mock_connect, mock_delete):
        mock_params.return_value = node_params()
        mock_delete.return_value = MagicMock()

        out = io.StringIO()
        with redirect_stdout(out):
            pods_delete.main()

        mock_delete.assert_called_once()
        self.assertIn('Pod deleted successfully', out.getvalue())

    @patch.object(pods_delete.common, 'delete_pod')
    @patch.object(pods_delete.common, 'connect')
    @patch.object(pods_delete.common, 'get_code_node_parameter_dictionary')
    def test_main_succeeds_when_pod_is_already_gone(
            self, mock_params, mock_connect, mock_delete):
        # Deleting is idempotent: a cleanup job that runs twice must not fail
        # the second time. delete_pod returns None only for a missing pod.
        mock_params.return_value = node_params()
        mock_delete.return_value = None

        out = io.StringIO()
        pods_delete.main()

        self.assertNotIn('Pod deleted successfully', out.getvalue())

    @patch.object(pods_delete.common, 'delete_pod')
    @patch.object(pods_delete.common, 'connect')
    @patch.object(pods_delete.common, 'get_code_node_parameter_dictionary')
    def test_main_exits_when_delete_fails(
            self, mock_params, mock_connect, mock_delete):
        # A real failure must not report success -- upstream printed
        # "Pod deleted successfully" and exited 0 for every failed delete.
        mock_params.return_value = node_params()
        mock_delete.side_effect = ApiException(status=500, reason='boom')

        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            pods_delete.main()

        self.assertEqual(1, cm.exception.code)
        self.assertNotIn('Pod deleted successfully', out.getvalue())

    @patch.object(pods_delete.common, 'connect')
    @patch.object(pods_delete.common, 'get_code_node_parameter_dictionary')
    def test_main_exits_when_pod_name_is_missing(self, mock_params, mock_connect):
        mock_params.return_value = node_params(name=None)

        with self.assertRaises(SystemExit) as cm:
            pods_delete.main()
        self.assertEqual(1, cm.exception.code)

    @patch.object(pods_delete.common, 'delete_pod')
    @patch.object(pods_delete.common, 'connect')
    @patch.object(pods_delete.common, 'get_code_node_parameter_dictionary')
    def test_main_exits_on_api_exception(self, mock_params, mock_connect, mock_delete):
        mock_params.return_value = node_params()
        mock_delete.side_effect = ApiException(status=500, reason='boom')

        with self.assertRaises(SystemExit) as cm:
            pods_delete.main()
        self.assertEqual(1, cm.exception.code)


if __name__ == '__main__':
    unittest.main()
