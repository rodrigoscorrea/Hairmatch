import io
import json
import logging
import sys

from django.test import SimpleTestCase
from opentelemetry.sdk.trace import TracerProvider

from hairmatch.logs import ExportErrorRateLimit, JsonFormatter, RedactionFilter, StripQueryString, TraceContextFilter


def make_logger(name, *filters):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    for item in filters:
        handler.addFilter(item)
    logger = logging.getLogger(name)
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger, stream


def lines(stream):
    return [json.loads(line) for line in stream.getvalue().splitlines()]


class JsonLineTests(SimpleTestCase):
    """TEL-36, TEL-37, TEL-38, TEL-40."""

    def test_each_record_is_one_json_line_with_ts_level_name_message(self):
        logger, stream = make_logger('t.json')
        logger.warning('hello %s', 'world')
        (line,) = lines(stream)
        self.assertEqual(line['level'], 'WARNING')
        self.assertEqual(line['name'], 't.json')
        self.assertEqual(line['message'], 'hello world')
        self.assertRegex(line['ts'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
        self.assertEqual(len(stream.getvalue().splitlines()), 1)

    def test_trace_and_span_ids_equal_the_active_span_ones(self):
        logger, stream = make_logger('t.trace', TraceContextFilter())
        with TracerProvider().get_tracer('t').start_as_current_span('s') as span:
            logger.info('inside')
        (line,) = lines(stream)
        self.assertEqual(line['trace_id'], format(span.get_span_context().trace_id, '032x'))
        self.assertEqual(line['span_id'], format(span.get_span_context().span_id, '016x'))
        self.assertRegex(line['trace_id'], r'^[0-9a-f]{32}$')
        self.assertRegex(line['span_id'], r'^[0-9a-f]{16}$')

    def test_without_a_span_the_ids_are_absent_and_formatting_does_not_fail(self):
        logger, stream = make_logger('t.nospan', TraceContextFilter())
        logger.info('outside')
        (line,) = lines(stream)
        self.assertNotIn('trace_id', line)
        self.assertNotIn('span_id', line)
        self.assertEqual(line['message'], 'outside')

    def test_exception_traceback_is_in_exc_info_of_the_same_line(self):
        logger, stream = make_logger('t.exc')
        try:
            raise ValueError('boom')
        except ValueError:
            logger.exception('failed')
        output = stream.getvalue()
        self.assertEqual(len(output.splitlines()), 1)
        (line,) = lines(stream)
        self.assertIn('Traceback (most recent call last)', line['exc_info'])
        self.assertIn('ValueError: boom', line['exc_info'])


class RedactionFilterTests(SimpleTestCase):
    """TEL-44, TEL-45, TEL-46."""

    def test_message_is_redacted_after_the_arguments_are_formatted(self):
        logger, stream = make_logger('t.red', RedactionFilter())
        logger.info('login of %s with cpf %s', 'ana@example.com', '123.456.789-09')
        (line,) = lines(stream)
        self.assertEqual(line['message'], 'login of [email] with cpf [cpf]')

    def test_traceback_text_is_redacted(self):
        logger, stream = make_logger('t.redexc', RedactionFilter())
        try:
            raise ValueError('duplicate key for ana@example.com phone (92) 99999-9999')
        except ValueError:
            logger.exception('failed')
        (line,) = lines(stream)
        self.assertIn('ValueError: duplicate key for [email] phone [telefone]', line['exc_info'])
        self.assertNotIn('ana@example.com', line['exc_info'])

    def test_stack_text_is_kept_in_stack_info(self):
        logger, stream = make_logger('t.redstack', RedactionFilter())
        logger.info('here', stack_info=True)
        (line,) = lines(stream)
        self.assertIn('Stack (most recent call last)', line['stack_info'])

    def test_stack_text_with_personal_data_is_redacted(self):
        record = logging.LogRecord('t', logging.INFO, __file__, 1, 'm', (), None)
        record.stack_info = 'File "x.py" mail ana@example.com'
        clean = RedactionFilter().filter(record)
        self.assertEqual(clean.stack_info, 'File "x.py" mail [email]')

    def test_returns_a_copy_and_leaves_the_original_record_untouched(self):
        record = logging.LogRecord('t', logging.INFO, __file__, 1, 'user %s', ('ana@example.com',), None)
        clean = RedactionFilter().filter(record)
        self.assertIsNot(clean, record)
        self.assertEqual(record.getMessage(), 'user ana@example.com')
        self.assertEqual(clean.getMessage(), 'user [email]')

    def test_cached_exc_text_is_redacted_too(self):
        record = logging.LogRecord('t', logging.ERROR, __file__, 1, 'm', (), None)
        record.exc_text = 'Traceback ... ana@example.com'
        self.assertEqual(RedactionFilter().filter(record).exc_text, 'Traceback ... [email]')


class ExtraFieldsTests(SimpleTestCase):
    """The `extra` of a record is redacted too: Django puts the request, with its path and query string, there."""

    def test_text_extras_are_redacted_and_objects_are_dropped(self):
        logger, stream = make_logger('t.extra', RedactionFilter())
        logger.info('hello', extra={'who': 'ana@example.com', 'count': 3, 'request': object(), 'flag': True})
        (line,) = lines(stream)
        self.assertEqual((line['who'], line['count'], line['flag']), ('[email]', 3, True))
        self.assertNotIn('request', line)

    def test_original_record_keeps_its_extras(self):
        record = logging.LogRecord('t', logging.INFO, __file__, 1, 'm', (), None)
        record.who = 'ana@example.com'
        record.request = object()
        RedactionFilter().filter(record)
        self.assertEqual(record.who, 'ana@example.com')
        self.assertTrue(hasattr(record, 'request'))


class ExportErrorRateLimitTests(SimpleTestCase):
    """TEL-15: at most one error line per signal every 60 s."""

    def setUp(self):
        self.now = 1000.0
        self.limit = ExportErrorRateLimit(clock=lambda: self.now)

    def record(self, name, level=logging.ERROR):
        return logging.LogRecord(name, level, __file__, 1, 'failed', (), None)

    def test_second_error_of_the_same_signal_inside_the_window_is_dropped(self):
        name = 'opentelemetry.exporter.otlp.proto.http.trace_exporter'
        self.assertTrue(self.limit.filter(self.record(name)))
        self.now += 59
        self.assertFalse(self.limit.filter(self.record(name)))

    def test_error_after_the_window_passes_again(self):
        name = 'opentelemetry.exporter.otlp.proto.http.trace_exporter'
        self.assertTrue(self.limit.filter(self.record(name)))
        self.now += 60
        self.assertTrue(self.limit.filter(self.record(name)))

    def test_each_signal_has_its_own_budget(self):
        names = [
            'opentelemetry.exporter.otlp.proto.http.trace_exporter',
            'opentelemetry.exporter.otlp.proto.http.metric_exporter',
            'opentelemetry.exporter.otlp.proto.http._log_exporter',
        ]
        self.assertEqual([self.limit.filter(self.record(n)) for n in names], [True, True, True])
        self.assertEqual([self.limit.filter(self.record(n)) for n in names], [False, False, False])

    def test_sdk_batch_loggers_count_for_their_signal(self):
        self.assertTrue(self.limit.filter(self.record('opentelemetry.exporter.otlp.proto.http.trace_exporter')))
        self.assertFalse(self.limit.filter(self.record('opentelemetry.sdk.trace.export')))

    def test_records_below_warning_are_never_dropped(self):
        name = 'opentelemetry.sdk.trace.export'
        self.assertTrue(self.limit.filter(self.record(name, logging.ERROR)))
        self.assertTrue(self.limit.filter(self.record(name, logging.INFO)))


class StripQueryStringTests(SimpleTestCase):
    """TEL-43."""

    def test_access_log_path_has_no_query_string_and_no_socket(self):
        logger, stream = make_logger('t.access', StripQueryString())
        logger.info('"%s" %s %s', 'GET /api/postal-codes/69000000?x=1&email=a@b.co HTTP/1.1', '200', '45', extra={'request': sys.stdout, 'server_time': 't'})
        (line,) = lines(stream)
        self.assertEqual(line['message'], '"GET /api/postal-codes/69000000 HTTP/1.1" 200 45')
        self.assertNotIn('request', line)

    def test_request_line_that_is_not_three_parts_is_left_alone(self):
        logger, stream = make_logger('t.access2', StripQueryString())
        logger.info('"%s" %s %s', '', '400', '0')
        (line,) = lines(stream)
        self.assertEqual(line['message'], '"" 400 0')
