"""
Unit tests for pods-create.py.

pods-create.py has a hyphenated filename, so it is loaded with importlib. It does
"import common", which resolves through the inserted sys.path to a module object
distinct from contents.common, so patches target pods_create.common.
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

pods_create = importlib.import_module('pods-create')


def create_data(**overrides):
    data = {
        'name': 'my-pod',
        'namespace': 'default',
        'container_name': 'app',
        'api_version': 'v1',
        'image': 'nginx:latest',
        'labels': 'app=web,env=prod',
        'ports': None,
    }
    data.update(overrides)
    return data


class TestCreatePod(unittest.TestCase):

    def setUp(self):
        os.environ.clear()

    def test_create_pod_builds_metadata_from_labels(self):
        pod = pods_create.create_pod(create_data())

        self.assertEqual('Pod', pod.kind)
        self.assertEqual('v1', pod.api_version)
        self.assertEqual('my-pod', pod.metadata.name)
        self.assertEqual('default', pod.metadata.namespace)
        self.assertEqual({'app': 'web', 'env': 'prod'}, pod.metadata.labels)


class TestPodsCreateMain(unittest.TestCase):

    def setUp(self):
        os.environ.clear()

    def _configure(self):
        os.environ['RD_CONFIG_NAME'] = 'my-pod'
        os.environ['RD_CONFIG_NAMESPACE'] = 'default'
        os.environ['RD_CONFIG_CONTAINER_NAME'] = 'app'
        os.environ['RD_CONFIG_API_VERSION'] = 'v1'
        os.environ['RD_CONFIG_IMAGE'] = 'nginx:latest'
        os.environ['RD_CONFIG_LABELS'] = 'app=web'

    @patch.object(pods_create.core_v1_api, 'CoreV1Api')
    @patch.object(pods_create.common, 'log_pod_parameters')
    @patch.object(pods_create.common, 'connect')
    def test_main_creates_the_pod(self, mock_connect, mock_log, mock_api_class):
        self._configure()
        mock_api_class.return_value.create_namespaced_pod.return_value = MagicMock()

        out = io.StringIO()
        with redirect_stdout(out):
            pods_create.main()

        kwargs = mock_api_class.return_value.create_namespaced_pod.call_args[1]
        self.assertEqual('default', kwargs['namespace'])
        self.assertEqual('my-pod', kwargs['body'].metadata.name)
        self.assertIn('Pod Created successfully', out.getvalue())

    @patch.object(pods_create.core_v1_api, 'CoreV1Api')
    @patch.object(pods_create.common, 'log_pod_parameters')
    @patch.object(pods_create.common, 'connect')
    def test_main_exits_on_api_exception(self, mock_connect, mock_log, mock_api_class):
        self._configure()
        mock_api_class.return_value.create_namespaced_pod.side_effect = ApiException(
            status=409, reason='AlreadyExists')

        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as cm:
            pods_create.main()
        self.assertEqual(1, cm.exception.code)

    @patch.object(pods_create.core_v1_api, 'CoreV1Api')
    @patch.object(pods_create.common, 'log_pod_parameters')
    @patch.object(pods_create.common, 'connect')
    def test_main_passes_optional_settings_through(
            self, mock_connect, mock_log, mock_api_class):
        self._configure()
        os.environ['RD_CONFIG_PORTS'] = '8080'
        os.environ['RD_CONFIG_ENVIRONMENTS'] = 'KEY=value'
        mock_api_class.return_value.create_namespaced_pod.return_value = MagicMock()

        with redirect_stdout(io.StringIO()):
            pods_create.main()

        container = mock_api_class.return_value.create_namespaced_pod.call_args[1][
            'body'].spec.containers[0]
        self.assertEqual('nginx:latest', container.image)
        self.assertEqual('app', container.name)


if __name__ == '__main__':
    unittest.main()
