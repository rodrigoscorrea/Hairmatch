from unittest import mock

from django.test import SimpleTestCase
from opentelemetry.metrics import NoOpMeter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import AggregationTemporality, InMemoryMetricReader
from opentelemetry.sdk.metrics import Counter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import NoOpTracer, StatusCode

from hairmatch import telemetry


class _Local:
    """A private SDK pair, so the tests do not depend on the process-wide providers."""

    def setUpTelemetry(self):
        self.reader = InMemoryMetricReader(preferred_temporality={Counter: AggregationTemporality.DELTA})
        self.meter_provider = MeterProvider(metric_readers=[self.reader])
        self.exporter = InMemorySpanExporter()
        self.tracer_provider = TracerProvider()
        self.tracer_provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        telemetry._counters.clear()
        telemetry._warned.clear()
        for patcher in (
            mock.patch.object(telemetry, '_meter', lambda: self.meter_provider.get_meter('hairmatch')),
            mock.patch.object(telemetry, '_tracer', lambda: self.tracer_provider.get_tracer('hairmatch')),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def points(self, name):
        """The data points of `name` seen so far. The delta reader empties on each read, so they accumulate here."""
        if not hasattr(self, '_seen'):
            self._seen = {}
        data = self.reader.get_metrics_data()
        for resource in (data.resource_metrics if data else []):
            for scope in resource.scope_metrics:
                for metric in scope.metrics:
                    self._seen.setdefault(metric.name, []).extend(
                        (dict(p.attributes), p.value) for p in metric.data.data_points
                    )
        return self._seen.get(name, [])


class NoSdkTests(SimpleTestCase):
    """TEL-12: with the SDK absent every helper is a no-op that does not raise."""

    def setUp(self):
        telemetry._counters.clear()
        for patcher in (
            mock.patch.object(telemetry, '_meter', lambda: NoOpMeter('hairmatch')),
            mock.patch.object(telemetry, '_tracer', lambda: NoOpTracer()),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_every_counter_helper_returns_none_without_raising(self):
        calls = [
            lambda: telemetry.count_problem('not-found', 404),
            lambda: telemetry.count_reserve_created('app'),
            lambda: telemetry.count_push('published'),
            lambda: telemetry.count_auth_rejection('missing'),
            lambda: telemetry.count_signup('created'),
            lambda: telemetry.count_upload('profile', 'stored'),
            lambda: telemetry.count_cep_lookup('cache'),
            lambda: telemetry.count_ai_request('profile', 'ok'),
            lambda: telemetry.count_ai_tokens('profile', 'input', 3),
        ]
        for call in calls:
            self.assertIsNone(call())

    def test_span_runs_its_body_and_yields_a_span(self):
        ran = []
        with telemetry.span('work', **{'a.b': 1}) as current:
            ran.append(current)
        self.assertEqual(len(ran), 1)

    def test_set_span_attributes_and_gemini_call_do_not_raise(self):
        telemetry.set_span_attributes(**{'hairmatch.reserve_id': 7})
        with telemetry.gemini_call('profile', 'gemini-2.0-flash') as call:
            call.record_usage(object())


class SdkFailureTests(SimpleTestCase):
    """TEL-13: an exception from the SDK inside a helper does not reach the view."""

    def setUp(self):
        telemetry._counters.clear()

    def test_counter_whose_meter_raises_does_not_propagate(self):
        with mock.patch.object(telemetry, '_meter', side_effect=RuntimeError('sdk down')):
            self.assertIsNone(telemetry.count_push('published'))

    def test_counter_whose_add_raises_does_not_propagate(self):
        meter = mock.Mock()
        meter.create_counter.return_value.add.side_effect = RuntimeError('add failed')
        with mock.patch.object(telemetry, '_meter', return_value=meter):
            self.assertIsNone(telemetry.count_signup('created'))
        meter.create_counter.return_value.add.assert_called_once()

    def test_span_whose_tracer_raises_still_runs_the_body_and_returns_its_value(self):
        with mock.patch.object(telemetry, '_tracer', side_effect=RuntimeError('sdk down')):
            with telemetry.span('work') as current:
                result = 42
        self.assertEqual(result, 42)
        self.assertIsNone(current)

    def test_span_exit_failure_does_not_propagate(self):
        manager = mock.MagicMock()
        manager.__exit__.side_effect = RuntimeError('end failed')
        tracer = mock.Mock()
        tracer.start_as_current_span.return_value = manager
        with mock.patch.object(telemetry, '_tracer', return_value=tracer):
            with telemetry.span('work'):
                pass

    def test_body_exception_still_propagates_when_the_sdk_fails(self):
        with mock.patch.object(telemetry, '_tracer', side_effect=RuntimeError('sdk down')):
            with self.assertRaisesMessage(KeyError, 'body'):
                with telemetry.span('work'):
                    raise KeyError('body')

    def test_set_span_attributes_failure_does_not_propagate(self):
        with mock.patch('opentelemetry.trace.get_current_span', side_effect=RuntimeError('boom')):
            self.assertIsNone(telemetry.set_span_attributes(a=1))


class CounterTests(_Local, SimpleTestCase):
    """TEL-50 to TEL-59: names, labels and values."""

    def setUp(self):
        self.setUpTelemetry()

    def test_each_counter_adds_one_with_its_labels(self):
        cases = [
            (lambda: telemetry.count_problem('not-found', 404), 'hairmatch.problems', {'slug': 'not-found', 'status': 404}),
            (lambda: telemetry.count_reserve_created('whatsapp'), 'hairmatch.reserves.created', {'channel': 'whatsapp'}),
            (lambda: telemetry.count_push('endpoint_gone'), 'hairmatch.push.results', {'outcome': 'endpoint_gone'}),
            (lambda: telemetry.count_auth_rejection('expired'), 'hairmatch.auth.rejections', {'reason': 'expired'}),
            (lambda: telemetry.count_signup('throttled'), 'hairmatch.signup.events', {'step': 'throttled'}),
            (lambda: telemetry.count_upload('gallery', 'invalid_image'), 'hairmatch.uploads', {'kind': 'gallery', 'outcome': 'invalid_image'}),
            (lambda: telemetry.count_cep_lookup('not_found'), 'hairmatch.cep.lookups', {'source': 'not_found'}),
            (lambda: telemetry.count_ai_request('chatbot', 'error'), 'hairmatch.ai.requests', {'feature': 'chatbot', 'outcome': 'error'}),
        ]
        for call, name, labels in cases:
            with self.subTest(name=name):
                call()
                self.assertEqual(self.points(name), [(labels, 1)])

    def test_tokens_add_the_amount_with_feature_and_direction(self):
        telemetry.count_ai_tokens('profile', 'output', 37)
        self.assertEqual(self.points('hairmatch.ai.tokens'), [({'feature': 'profile', 'direction': 'output'}, 37)])

    def test_tokens_that_are_not_a_positive_int_are_not_recorded(self):
        for amount in (0, -1, True, 2.5, None, '7'):
            telemetry.count_ai_tokens('profile', 'input', amount)
        self.assertEqual(self.points('hairmatch.ai.tokens'), [])

    def test_the_nine_counters_are_the_ones_of_the_spec(self):
        self.assertEqual(
            sorted(telemetry.COUNTERS),
            sorted([
                'hairmatch.problems', 'hairmatch.reserves.created', 'hairmatch.push.results',
                'hairmatch.auth.rejections', 'hairmatch.signup.events', 'hairmatch.uploads',
                'hairmatch.cep.lookups', 'hairmatch.ai.requests', 'hairmatch.ai.tokens',
            ]),
        )

    def test_a_value_outside_the_closed_set_is_not_recorded(self):
        telemetry.count_reserve_created('ana@example.com')
        telemetry.count_push('exploded')
        telemetry.count_upload('avatar', 'stored')
        telemetry.count_problem('made-up-slug', 404)
        telemetry.count_problem('not-found', 200)
        telemetry.count_problem('not-found', '404')
        for name in ('hairmatch.reserves.created', 'hairmatch.push.results', 'hairmatch.uploads', 'hairmatch.problems'):
            self.assertEqual(self.points(name), [], name)

    def test_the_label_names_of_every_counter_are_the_ones_listed(self):
        self.assertEqual({n: sorted(spec[1]) for n, spec in telemetry.COUNTERS.items()}, {
            'hairmatch.problems': ['slug', 'status'],
            'hairmatch.reserves.created': ['channel'],
            'hairmatch.push.results': ['outcome'],
            'hairmatch.auth.rejections': ['reason'],
            'hairmatch.signup.events': ['step'],
            'hairmatch.uploads': ['kind', 'outcome'],
            'hairmatch.cep.lookups': ['source'],
            'hairmatch.ai.requests': ['feature', 'outcome'],
            'hairmatch.ai.tokens': ['direction', 'feature'],
        })


class SpanTests(_Local, SimpleTestCase):
    def setUp(self):
        self.setUpTelemetry()

    def test_span_is_a_child_with_the_attributes(self):
        tracer = self.tracer_provider.get_tracer('t')
        with tracer.start_as_current_span('parent') as parent:
            with telemetry.span('child', **{'image.bytes_in': 10, 'skipped': None}):
                pass
        child, parent_span = self.exporter.get_finished_spans()
        self.assertEqual(child.name, 'child')
        self.assertEqual(child.parent.span_id, parent.get_span_context().span_id)
        self.assertEqual(dict(child.attributes), {'image.bytes_in': 10})

    def test_exception_marks_the_span_with_the_type_only_and_propagates(self):
        with self.assertRaises(ValueError):
            with telemetry.span('work'):
                raise ValueError('secret ana@example.com')
        (finished,) = self.exporter.get_finished_spans()
        self.assertEqual(finished.status.status_code, StatusCode.ERROR)
        self.assertEqual(finished.status.description, 'ValueError')
        self.assertEqual(finished.attributes['error.type'], 'ValueError')
        self.assertEqual(finished.events, ())

    def test_set_span_attributes_sets_on_the_active_span_and_drops_none(self):
        tracer = self.tracer_provider.get_tracer('t')
        with tracer.start_as_current_span('request'):
            telemetry.set_span_attributes(**{'hairmatch.reserve_id': 7, 'hairmatch.hairdresser_id': 3, 'x': None})
        (finished,) = self.exporter.get_finished_spans()
        self.assertEqual(dict(finished.attributes), {'hairmatch.reserve_id': 7, 'hairmatch.hairdresser_id': 3})


class GeminiCallTests(_Local, SimpleTestCase):
    """TEL-25 to TEL-27, TEL-58, TEL-59."""

    def setUp(self):
        self.setUpTelemetry()

    def response(self, prompt, candidates):
        return mock.Mock(usage_metadata=mock.Mock(prompt_token_count=prompt, candidates_token_count=candidates))

    def test_success_records_span_attributes_tokens_and_an_ok_request(self):
        with telemetry.gemini_call('profile', 'gemini-2.0-flash') as call:
            call.record_usage(self.response(120, 45))
        (finished,) = self.exporter.get_finished_spans()
        self.assertEqual(finished.name, 'gemini generate_content')
        self.assertEqual(dict(finished.attributes), {
            'gen_ai.request.model': 'gemini-2.0-flash', 'hairmatch.ai.feature': 'profile',
            'gen_ai.usage.input_tokens': 120, 'gen_ai.usage.output_tokens': 45,
        })
        self.assertEqual(self.points('hairmatch.ai.requests'), [({'feature': 'profile', 'outcome': 'ok'}, 1)])
        self.assertCountEqual(self.points('hairmatch.ai.tokens'), [
            ({'feature': 'profile', 'direction': 'input'}, 120), ({'feature': 'profile', 'direction': 'output'}, 45),
        ])

    def test_response_without_token_counts_records_no_token_attributes(self):
        with telemetry.gemini_call('chatbot', 'gemini-2.0-flash') as call:
            call.record_usage(mock.Mock(usage_metadata=None))
            call.record_usage(object())
        (finished,) = self.exporter.get_finished_spans()
        self.assertNotIn('gen_ai.usage.input_tokens', finished.attributes)
        self.assertEqual(self.points('hairmatch.ai.tokens'), [])

    def test_exception_ends_the_span_in_error_counts_an_error_and_propagates_the_same_exception(self):
        failure = ConnectionError('api down')
        with self.assertRaises(ConnectionError) as caught:
            with telemetry.gemini_call('chatbot', 'gemini-2.0-flash'):
                raise failure
        self.assertIs(caught.exception, failure)
        (finished,) = self.exporter.get_finished_spans()
        self.assertEqual(finished.status.status_code, StatusCode.ERROR)
        self.assertEqual(finished.attributes['error.type'], 'ConnectionError')
        self.assertEqual(self.points('hairmatch.ai.requests'), [({'feature': 'chatbot', 'outcome': 'error'}, 1)])

    def test_span_and_attributes_never_hold_the_prompt_or_the_answer(self):
        with telemetry.gemini_call('profile', 'gemini-2.0-flash') as call:
            call.record_usage(self.response(1, 2))
        (finished,) = self.exporter.get_finished_spans()
        self.assertEqual(
            sorted(finished.attributes),
            ['gen_ai.request.model', 'gen_ai.usage.input_tokens', 'gen_ai.usage.output_tokens', 'hairmatch.ai.feature'],
        )
