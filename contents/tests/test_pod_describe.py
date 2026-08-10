"""
Unit tests for pod-describe.py.

pod-describe.py has a hyphenated filename, so it is loaded with importlib. It does
"import common", which resolves through the inserted sys.path to a module object
distinct from contents.common, so patches target pod_describe.common.
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

pod_describe = importlib.import_module('pod-describe')


class TestPodDescribe(unittest.TestCase):

    def setUp(self):
        os.environ.clear()

    @patch.object(pod_describe.client, 'CoreV1Api')
    @patch.object(pod_describe.common, 'connect')
    def test_main_describes_pod_named_by_config(self, mock_connect, mock_api_class):
        os.environ['RD_CONFIG_NAME'] = 'my-pod'
        os.environ['RD_CONFIG_NAMESPACE'] = 'prod'
        mock_api_class.return_value.read_namespaced_pod.return_value = MagicMock(
            status={'phase': 'Running'})

        out = io.StringIO()
        with redirect_stdout(out):
            pod_describe.main()

        mock_api_class.return_value.read_namespaced_pod.assert_called_once_with(
            name='my-pod', namespace='prod')
        self.assertIn('Running', out.getvalue())

    @patch.object(pod_describe.client, 'CoreV1Api')
    @patch.object(pod_describe.common, 'connect')
    @patch.object(pod_describe.common, 'get_core_node_parameter_list')
    def test_main_falls_back_to_node_parameters(
            self, mock_params, mock_connect, mock_api_class):
        mock_params.return_value = ['node-pod', 'staging', 'app']
        mock_api_class.return_value.read_namespaced_pod.return_value = MagicMock(
            status={'phase': 'Running'})

        with redirect_stdout(io.StringIO()):
            pod_describe.main()

        mock_api_class.return_value.read_namespaced_pod.assert_called_once_with(
            name='node-pod', namespace='staging')

    @patch.object(pod_describe.client, 'CoreV1Api')
    @patch.object(pod_describe.common, 'connect')
    def test_main_uses_node_namespace_when_step_sets_only_the_name(
            self, mock_connect, mock_api_class):
        # A node in namespace "prod" with the step's Pod Name filled in but
        # Namespace blank must still describe prod/my-pod, not default/my-pod.
        os.environ['RD_CONFIG_NAME'] = 'my-pod'
        os.environ['RD_NODE_DEFAULT_NAMESPACE'] = 'prod'
        mock_api_class.return_value.read_namespaced_pod.return_value = MagicMock(
            status={'phase': 'Running'})

        with redirect_stdout(io.StringIO()):
            pod_describe.main()

        mock_api_class.return_value.read_namespaced_pod.assert_called_once_with(
            name='my-pod', namespace='prod')

    @patch.object(pod_describe.client, 'CoreV1Api')
    @patch.object(pod_describe.common, 'connect')
    def test_main_exits_when_pod_name_is_missing(self, mock_connect, mock_api_class):
        with self.assertRaises(SystemExit) as cm:
            pod_describe.main()
        self.assertEqual(1, cm.exception.code)

    @patch.object(pod_describe.client, 'CoreV1Api')
    @patch.object(pod_describe.common, 'connect')
    def test_main_exits_on_api_exception(self, mock_connect, mock_api_class):
        os.environ['RD_CONFIG_NAME'] = 'my-pod'
        os.environ['RD_CONFIG_NAMESPACE'] = 'prod'
        mock_api_class.return_value.read_namespaced_pod.side_effect = ApiException(
            status=404, reason='Not Found')

        with self.assertRaises(SystemExit) as cm:
            pod_describe.main()
        self.assertEqual(1, cm.exception.code)


if __name__ == '__main__':
    unittest.main()
