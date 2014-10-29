# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from mock import patch
from tornado import web, gen, testing
from raven.contrib.tornado import SentryMixin, AsyncSentryClient
from raven.utils import six


class AnErrorProneHandler(SentryMixin, web.RequestHandler):
    def get(self):
        try:
            raise Exception("Damn it!")
        except Exception:
            self.captureException(True)


@web.stream_request_body
class AnErrorProneStreamingHandler(SentryMixin, web.RequestHandler):
    def get(self):
        try:
            raise Exception("Damn it!")
        except Exception:
            self.captureException(True)


class AnErrorWithCustomNonDictData(SentryMixin, web.RequestHandler):
    def get(self):
        try:
            raise Exception("Oops")
        except Exception:
            self.captureException(True, data="extra custom non-dict data")


class AnErrorWithCustomDictData(SentryMixin, web.RequestHandler):
    def get(self):
        try:
            raise Exception("Oops")
        except Exception:
            self.captureException(True, data={'extra': {'extra_data': 'extra custom dict data'}})


class SendErrorTestHandler(SentryMixin, web.RequestHandler):
    def get(self):
        raise Exception("Oops")


class SendErrorAsyncHandler(SentryMixin, web.RequestHandler):
    @web.asynchronous
    @gen.engine
    def get(self):
        raise Exception("Oops")


class AsyncMessageHandler(SentryMixin, web.RequestHandler):
    @web.asynchronous
    @gen.engine
    def get(self):
        # Compute something crazy
        yield gen.Task(
            self.captureMessage, "Something totally crazy was just done"
        )
        self.set_header('X-Sentry-ID', 'The ID')
        self.finish()

    def get_current_user(self):
        return {
            'name': 'John Doe'
        }


class TornadoAsyncClientTestCase(testing.AsyncHTTPTestCase):
    def get_app(self):
        app = web.Application([
            web.url(r'/an-error', AnErrorProneHandler),
            web.url(r'/a-streaming-error', AnErrorProneStreamingHandler),
            web.url(r'/an-async-message', AsyncMessageHandler),
            web.url(r'/send-error', SendErrorTestHandler),
            web.url(r'/send-error-async', SendErrorAsyncHandler),
            web.url(r'/an-error-with-custom-non-dict-data', AnErrorWithCustomNonDictData),
            web.url(r'/an-error-with-custom-dict-data', AnErrorWithCustomDictData),
        ])
        app.sentry_client = AsyncSentryClient(
            'http://public_key:secret_key@host:9000/project'
        )
        return app

    @patch('raven.contrib.tornado.AsyncSentryClient.send')
    def test_error_handler(self, send):
        response = self.fetch('/an-error?qs=qs')
        self.assertEqual(response.code, 200)
        self.assertEqual(send.call_count, 1)
        args, kwargs = send.call_args

        assert 'user' in kwargs
        assert 'request' in kwargs
        assert 'exception' in kwargs

        http_data = kwargs['request']
        self.assertEqual(http_data['cookies'], None)
        self.assertEqual(http_data['url'], response.effective_url)
        self.assertEqual(http_data['query_string'], 'qs=qs')
        self.assertEqual(http_data['method'], 'GET')

        user_data = kwargs['user']
        self.assertEqual(user_data['is_authenticated'], False)

    @patch('raven.contrib.tornado.AsyncSentryClient.send_encoded')
    def test_streaming_error_handler(self, send_encoded):
        response = self.fetch('/a-streaming-error?qs=qs')
        self.assertEqual(response.code, 200)
        self.assertEqual(send_encoded.call_count, 1)
        encoded = send_encoded.call_args[0][0]
        decoded = self._app.sentry_client.decode(encoded)

        assert 'user' in decoded
        assert 'request' in decoded
        assert 'exception' in decoded

        http_data = decoded['request']
        self.assertEqual(http_data['cookies'], None)
        self.assertEqual(http_data['url'], response.effective_url)
        self.assertEqual(http_data['query_string'], 'qs=qs')
        self.assertEqual(http_data['method'], 'GET')

        user_data = decoded['user']
        self.assertEqual(user_data['is_authenticated'], False)

    @patch('raven.contrib.tornado.AsyncSentryClient.send')
    def test_error_with_custom_non_dict_data_handler(self, send):
        response = self.fetch('/an-error-with-custom-non-dict-data?qs=qs')
        self.assertEqual(response.code, 200)
        self.assertEqual(send.call_count, 1)
        args, kwargs = send.call_args

        assert 'user' in kwargs
        assert 'request' in kwargs
        assert 'exception' in kwargs
        assert 'extra' in kwargs

        http_data = kwargs['request']
        self.assertEqual(http_data['cookies'], None)
        self.assertEqual(http_data['url'], response.effective_url)
        self.assertEqual(http_data['query_string'], 'qs=qs')
        self.assertEqual(http_data['method'], 'GET')

        user_data = kwargs['user']
        self.assertEqual(user_data['is_authenticated'], False)

        assert 'extra_data' in kwargs['extra']
        if six.PY3:
            expected = "'extra custom non-dict data'"
        else:
            expected = "u'extra custom non-dict data'"
        assert kwargs['extra']['extra_data'] == expected

    @patch('raven.contrib.tornado.AsyncSentryClient.send')
    def test_error_with_custom_dict_data_handler(self, send):
        response = self.fetch('/an-error-with-custom-dict-data?qs=qs')
        self.assertEqual(response.code, 200)
        self.assertEqual(send.call_count, 1)
        args, kwargs = send.call_args

        assert 'user' in kwargs
        assert 'request' in kwargs
        assert 'exception' in kwargs
        assert 'extra' in kwargs

        http_data = kwargs['request']
        self.assertEqual(http_data['cookies'], None)
        self.assertEqual(http_data['url'], response.effective_url)
        self.assertEqual(http_data['query_string'], 'qs=qs')
        self.assertEqual(http_data['method'], 'GET')

        user_data = kwargs['user']
        self.assertEqual(user_data['is_authenticated'], False)

        assert 'extra_data' in kwargs['extra']
        if six.PY3:
            expected = "'extra custom dict data'"
        else:
            expected = "u'extra custom dict data'"
        assert kwargs['extra']['extra_data'] == expected

    @patch(
        'raven.contrib.tornado.AsyncSentryClient.send',
        side_effect=lambda *args, **kwargs: kwargs['callback']("done"))
    def test_message_handler(self, send):
        response = self.fetch('/an-async-message?qs=qs')
        self.assertEqual(response.code, 200)
        self.assertEqual(send.call_count, 1)
        args, kwargs = send.call_args

        assert 'user' in kwargs
        assert 'request' in kwargs
        assert 'sentry.interfaces.Message' in kwargs

        http_data = kwargs['request']
        self.assertEqual(http_data['cookies'], None)
        self.assertEqual(http_data['url'], response.effective_url)
        self.assertEqual(http_data['query_string'], 'qs=qs')
        self.assertEqual(http_data['method'], 'GET')

        user_data = kwargs['user']
        self.assertEqual(user_data['is_authenticated'], True)

    @patch('raven.contrib.tornado.AsyncSentryClient.send')
    def test_send_error_handler(self, send):
        response = self.fetch('/send-error?qs=qs')
        self.assertEqual(response.code, 500)
        self.assertEqual(send.call_count, 1)
        args, kwargs = send.call_args

        assert 'user' in kwargs
        assert 'request' in kwargs
        assert 'exception' in kwargs

        http_data = kwargs['request']
        self.assertEqual(http_data['cookies'], None)
        self.assertEqual(http_data['url'], response.effective_url)
        self.assertEqual(http_data['query_string'], 'qs=qs')
        self.assertEqual(http_data['method'], 'GET')

        user_data = kwargs['user']
        self.assertEqual(user_data['is_authenticated'], False)

    @patch('raven.contrib.tornado.AsyncSentryClient.send')
    def test_send_error_handler_async(self, send):
        response = self.fetch('/send-error-async?qs=qs')
        self.assertEqual(response.code, 500)
        self.assertEqual(send.call_count, 1)
        args, kwargs = send.call_args

        assert 'user' in kwargs
        assert 'request' in kwargs
        assert 'exception' in kwargs

        http_data = kwargs['request']
        self.assertEqual(http_data['cookies'], None)
        self.assertEqual(http_data['url'], response.effective_url)
        self.assertEqual(http_data['query_string'], 'qs=qs')
        self.assertEqual(http_data['method'], 'GET')

        user_data = kwargs['user']
        self.assertEqual(user_data['is_authenticated'], False)
