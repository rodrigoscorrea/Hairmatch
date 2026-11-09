import sys
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from hairmatch import profiling

ADDRESS = 'http://pyroscope:4040'


def fresh_state():
    profiling._init.update(done=False, enabled=False, failure=None, logged=False)


class ProfilingTestCase(SimpleTestCase):
    def setUp(self):
        fresh_state()
        self.addCleanup(fresh_state)
        self.configure = mock.Mock()
        patcher = mock.patch.dict(sys.modules, {'pyroscope': SimpleNamespace(configure=self.configure)})
        patcher.start()
        self.addCleanup(patcher.stop)


class DisabledTests(ProfilingTestCase):
    def test_address_absent_starts_nothing(self):
        self.assertFalse(profiling.init_profiling({}))
        self.configure.assert_not_called()

    def test_address_empty_or_blank_starts_nothing(self):
        for value in ('', '   '):
            fresh_state()
            self.assertFalse(profiling.init_profiling({'PYROSCOPE_SERVER_ADDRESS': value}))
        self.configure.assert_not_called()

    def test_disabled_does_not_import_the_sdk(self):
        with mock.patch.dict(sys.modules):
            sys.modules.pop('pyroscope')
            self.assertFalse(profiling.init_profiling({}))
            self.assertNotIn('pyroscope', sys.modules)


class EnabledTests(ProfilingTestCase):
    def test_configures_the_agent_with_the_address_the_service_name_and_the_environment(self):
        started = profiling.init_profiling({
            'PYROSCOPE_SERVER_ADDRESS': ADDRESS,
            'OTEL_SERVICE_NAME': 'hairmatch-test',
            'OTEL_RESOURCE_ATTRIBUTES': 'deployment.environment.name=staging',
        })
        self.assertTrue(started)
        self.configure.assert_called_once_with(
            application_name='hairmatch-test', server_address=ADDRESS, tags={'env': 'staging'},
        )

    def test_defaults_match_the_telemetry_ones(self):
        profiling.init_profiling({'PYROSCOPE_SERVER_ADDRESS': ADDRESS})
        self.configure.assert_called_once_with(
            application_name='hairmatch-api', server_address=ADDRESS, tags={'env': 'dev'},
        )

    def test_service_name_order(self):
        self.assertEqual(profiling.service_name({}), 'hairmatch-api')
        self.assertEqual(profiling.service_name({'OTEL_RESOURCE_ATTRIBUTES': 'a=b, service.name = from-attrs'}), 'from-attrs')
        self.assertEqual(
            profiling.service_name({'OTEL_SERVICE_NAME': 'explicit', 'OTEL_RESOURCE_ATTRIBUTES': 'service.name=from-attrs'}),
            'explicit',
        )
        self.assertEqual(profiling.service_name({'OTEL_SERVICE_NAME': '  '}), 'hairmatch-api')

    def test_calling_it_again_changes_nothing(self):
        env = {'PYROSCOPE_SERVER_ADDRESS': ADDRESS}
        self.assertTrue(profiling.init_profiling(env))
        self.assertTrue(profiling.init_profiling(env))
        self.configure.assert_called_once()


class FailureTests(ProfilingTestCase):
    def test_sdk_error_is_swallowed_and_logged_once_with_the_type_only(self):
        self.configure.side_effect = RuntimeError('boom http://user:secret@pyroscope:4040')
        with self.assertLogs('hairmatch.profiling', level='WARNING') as logs:
            self.assertFalse(profiling.init_profiling({'PYROSCOPE_SERVER_ADDRESS': ADDRESS}))
            profiling.log_init_failure()
            profiling.log_init_failure()
        self.assertEqual(len(logs.output), 1)
        self.assertIn('RuntimeError', logs.output[0])
        self.assertNotIn('secret', logs.output[0])

    def test_missing_sdk_is_a_start_failure_too(self):
        sys.modules['pyroscope'] = None  # makes `import pyroscope` raise ModuleNotFoundError
        with self.assertLogs('hairmatch.profiling', level='WARNING') as logs:
            self.assertFalse(profiling.init_profiling({'PYROSCOPE_SERVER_ADDRESS': ADDRESS}))
            profiling.log_init_failure()
        self.assertRegex(logs.output[0], 'ImportError|ModuleNotFoundError')

    def test_a_failed_start_is_not_retried(self):
        self.configure.side_effect = RuntimeError('boom')
        env = {'PYROSCOPE_SERVER_ADDRESS': ADDRESS}
        with self.assertLogs('hairmatch.profiling', level='WARNING'):
            profiling.init_profiling(env)
            profiling.init_profiling(env)
        self.configure.assert_called_once()

    def test_interrupt_still_propagates(self):
        self.configure.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            profiling.init_profiling({'PYROSCOPE_SERVER_ADDRESS': ADDRESS})
