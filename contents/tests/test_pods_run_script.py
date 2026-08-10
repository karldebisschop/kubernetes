"""
Unit tests for pods-run-script.py.

pods-run-script.py has a hyphenated filename, so it is loaded with importlib. It does
"import common", which resolves through the inserted sys.path to a module object
distinct from contents.common, so patches target pods_run_script.common.
"""

import importlib
import io
import os
import sys
import unittest

from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

pods_run_script = importlib.import_module('pods-run-script')


class TestPodsRunScript(unittest.TestCase):

    def setUp(self):
        os.environ.clear()

    def _run_main(self, mock_run_command, mock_interactive, stdout=b'ok', stderr=b''):
        resp = MagicMock()
        resp.peek_stdout.return_value = bool(stdout)
        resp.read_stdout.return_value = stdout
        resp.peek_stderr.return_value = bool(stderr)
        resp.read_stderr.return_value = stderr
        mock_run_command.return_value = resp
        mock_interactive.return_value = (resp, False)
        out = io.StringIO()
        with redirect_stdout(out):
            pods_run_script.main()
        return out.getvalue()

    @patch.object(pods_run_script.common, 'run_interactive_command')
    @patch.object(pods_run_script.common, 'run_command')
    @patch.object(pods_run_script.common, 'copy_file')
    @patch.object(pods_run_script.common, 'log_pod_parameters')
    @patch.object(pods_run_script.core_v1_api, 'CoreV1Api')
    @patch.object(pods_run_script.common, 'verify_pod_exists')
    @patch.object(pods_run_script.common, 'get_core_node_parameter_list')
    @patch.object(pods_run_script.common, 'connect')
    def test_main_copies_script_and_makes_it_executable(
            self, mock_connect, mock_params, mock_verify, mock_api_class,
            mock_log, mock_copy, mock_run_command, mock_interactive):
        os.environ['RD_CONFIG_SCRIPT'] = 'echo hello'
        mock_params.return_value = ['my-pod', 'default', 'app']
        mock_api_class.return_value.read_namespaced_pod.return_value = MagicMock()

        output = self._run_main(mock_run_command, mock_interactive)

        mock_copy.assert_called_once()
        self.assertEqual('my-pod', mock_copy.call_args[1]['name'])
        chmod = mock_run_command.call_args_list[0][1]['command']
        self.assertEqual(['chmod', '+x'], chmod[:2])
        self.assertIn('ok', output)

    @patch.object(pods_run_script.core_v1_api, 'CoreV1Api')
    @patch.object(pods_run_script.common, 'verify_pod_exists')
    @patch.object(pods_run_script.common, 'get_core_node_parameter_list')
    @patch.object(pods_run_script.common, 'connect')
    def test_main_exits_when_pod_is_missing(
            self, mock_connect, mock_params, mock_verify, mock_api_class):
        os.environ['RD_CONFIG_SCRIPT'] = 'echo hello'
        mock_params.return_value = ['my-pod', 'default', 'app']
        mock_api_class.return_value.read_namespaced_pod.return_value = None

        with self.assertRaises(SystemExit) as cm:
            pods_run_script.main()
        self.assertEqual(1, cm.exception.code)

    @patch.object(pods_run_script.common, 'run_interactive_command')
    @patch.object(pods_run_script.common, 'run_command')
    @patch.object(pods_run_script.common, 'copy_file')
    @patch.object(pods_run_script.common, 'log_pod_parameters')
    @patch.object(pods_run_script.client, 'CoreV1Api')
    @patch.object(pods_run_script.core_v1_api, 'CoreV1Api')
    @patch.object(pods_run_script.common, 'verify_pod_exists')
    @patch.object(pods_run_script.common, 'get_core_node_parameter_list')
    @patch.object(pods_run_script.common, 'connect')
    def test_main_resolves_first_container_when_none_configured(
            self, mock_connect, mock_params, mock_verify, mock_core_api,
            mock_client_api, mock_log, mock_copy, mock_run_command, mock_interactive):
        os.environ['RD_CONFIG_SCRIPT'] = 'echo hello'
        mock_params.return_value = ['my-pod', 'default', None]
        mock_core_api.return_value.read_namespaced_pod.return_value = MagicMock()
        status = MagicMock()
        status.spec.containers = [MagicMock()]
        status.spec.containers[0].name = 'sidecar'
        mock_client_api.return_value.read_namespaced_pod_status.return_value = status

        self._run_main(mock_run_command, mock_interactive)

        self.assertEqual('sidecar', mock_copy.call_args[1]['container'])


if __name__ == '__main__':
    unittest.main()
