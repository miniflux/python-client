# The MIT License (MIT)
#
# Copyright (c) Frederic Guillot
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import json
import time
import unittest
from unittest import mock

import miniflux
from miniflux import (
    AccessForbidden,
    AccessUnauthorized,
    BadRequest,
    ClientError,
    ResourceNotFound,
    ServerError,
)

import requests
from requests.exceptions import Timeout


class TestMinifluxClient(unittest.TestCase):
    def test_get_error_reason(self):
        response = mock.Mock()
        response.status_code = 404
        response.headers = {"Content-Type": "application/json"}
        response.json.return_value = {"error_message": "some error"}
        error = ResourceNotFound(response)
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.get_error_reason(), "some error")

    def test_default_session_not_shared(self):
        client_one = miniflux.Client("http://localhost", api_key="token-one")
        client_two = miniflux.Client("http://localhost", api_key="token-two")

        self.assertIsNot(client_one._session, client_two._session)
        self.assertEqual(client_one._session.headers.get("X-Auth-Token"), "token-one")
        self.assertEqual(client_two._session.headers.get("X-Auth-Token"), "token-two")

    def test_get_error_without_reason(self):
        response = mock.Mock()
        response.status_code = 404
        response.headers = {"Content-Type": "application/json"}
        response.json.return_value = {}
        error = ResourceNotFound(response)
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.get_error_reason(), "status_code=404")

    def test_get_error_with_bad_response(self):
        response = mock.Mock()
        response.status_code = 404
        response.headers = {"Content-Type": "application/json"}
        response.json.return_value = None
        error = ResourceNotFound(response)
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.get_error_reason(), "status_code=404")

    def test_get_error_reason_without_json_content_type(self):
        response = mock.Mock()
        response.status_code = 500
        response.headers = {"Content-Type": "text/html"}
        response.json = mock.Mock()

        error = ServerError(response)

        self.assertEqual(error.get_error_reason(), "status_code=500")
        response.json.assert_not_called()

    def test_get_error_reason_without_content_type_header(self):
        response = mock.Mock()
        response.status_code = 403
        response.headers = {}
        response.json = mock.Mock()

        error = AccessForbidden(response)

        self.assertEqual(error.get_error_reason(), "status_code=403")
        response.json.assert_not_called()

    def test_base_url_with_trailing_slash(self):
        session = requests.Session()
        expected_result = [{"url": "http://example.org/feed", "title": "Example", "type": "RSS"}]

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost/", "username", "password", session=session)
        result = client.discover("http://example.org/")

        session.post.assert_called_once_with(
            "http://localhost/v1/discover",
            data=mock.ANY,
            timeout=30.0,
        )
        self.assertEqual(session.auth, ("username", "password"))
        self.assertEqual(result, expected_result)

    def test_flush_history(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 202

        session.delete = mock.Mock()
        session.delete.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret", session=session)
        result = client.flush_history()

        session.delete.assert_called_once_with(
            "http://localhost/v1/flush-history",
            timeout=30.0,
        )
        self.assertEqual(session.headers.get("X-Auth-Token"), "secret")
        self.assertTrue(result)

    def test_get_version(self):
        session = requests.Session()
        expected_result = {
            "version": "dev",
            "commit": "HEAD",
            "build_date": "undefined",
            "go_version": "go1.21.1",
            "compiler": "gc",
            "arch": "amd64",
            "os": "darwin",
        }

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret", session=session)
        result = client.get_version()

        session.get.assert_called_once_with(
            "http://localhost/v1/version",
            timeout=30.0,
        )
        self.assertEqual(session.headers.get("X-Auth-Token"), "secret")
        self.assertEqual(result, expected_result)

    def test_get_me(self):
        session = requests.Session()
        expected_result = {"id": 123, "username": "foobar"}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.me()

        session.get.assert_called_once_with(
            "http://localhost/v1/me",
            timeout=30,
        )

        self.assertEqual(result, expected_result)

    def test_get_me_with_server_error(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 500

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)

        with self.assertRaises(ClientError):
            client.me()

    def test_discover(self):
        session = requests.Session()
        expected_result = [{"url": "http://example.org/feed", "title": "Example", "type": "RSS"}]

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.discover("http://example.org/")

        session.post.assert_called_once_with(
            "http://localhost/v1/discover",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("url"), "http://example.org/")
        self.assertIsNone(payload.get("username"))
        self.assertIsNone(payload.get("password"))
        self.assertEqual(result, expected_result)

    def test_discover_with_credentials(self):
        session = requests.Session()
        expected_result = [{"url": "http://example.org/feed", "title": "Example", "type": "RSS"}]

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.discover(
            "http://example.org/",
            username="foobar",
            password="secret",
            user_agent="Bot",
        )

        session.post.assert_called_once_with(
            "http://localhost/v1/discover",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("url"), "http://example.org/")
        self.assertEqual(payload.get("username"), "foobar")
        self.assertEqual(payload.get("password"), "secret")
        self.assertEqual(payload.get("user_agent"), "Bot")
        self.assertEqual(result, expected_result)

    def test_discover_with_server_error(self):
        session = requests.Session()
        expected_result = {"error_message": "some error"}

        response = mock.Mock()
        response.status_code = 500
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)

        with self.assertRaises(ClientError):
            client.discover("http://example.org/")

    def test_export(self):
        session = requests.Session()
        expected_result = "OPML feed"

        response = mock.Mock()
        response.status_code = 200
        response.text = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.export()

        session.get.assert_called_once_with(
            "http://localhost/v1/export",
            timeout=30,
        )

        self.assertEqual(result, expected_result)

    def test_import(self):
        session = requests.Session()
        input_data = "my opml data"

        response = mock.Mock()
        response.status_code = 201

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        client.import_feeds(input_data)

        session.post.assert_called_once_with(
            "http://localhost/v1/import",
            data=input_data,
            timeout=30,
        )

    def test_import_failure(self):
        session = requests.Session()
        input_data = "my opml data"

        response = mock.Mock()
        response.status_code = 500
        response.json.return_value = {"error_message": "random error"}

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)

        with self.assertRaises(ClientError):
            client.import_feeds(input_data)

        session.post.assert_called_once_with(
            "http://localhost/v1/import",
            data=input_data,
            timeout=30,
        )

    def test_get_feed(self):
        session = requests.Session()
        expected_result = {"id": 123, "title": "Example"}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_feed(123)

        session.get.assert_called_once_with(
            "http://localhost/v1/feeds/123",
            timeout=30,
        )

        self.assertEqual(result, expected_result)

    def test_get_feed_icon(self):
        session = requests.Session()
        expected_result = {
            "id": 11,
            "mime_type": "image/x-icon",
            "data": "image/x-icon;base64,data",
        }

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_icon_by_feed_id(123)

        session.get.assert_called_once_with(
            "http://localhost/v1/feeds/123/icon",
            timeout=30.0,
        )

        self.assertEqual(result, expected_result)

    def test_get_icon(self):
        session = requests.Session()
        expected_result = {
            "id": 11,
            "mime_type": "image/x-icon",
            "data": "image/x-icon;base64,data",
        }

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_icon(11)

        session.get.assert_called_once_with(
            "http://localhost/v1/icons/11",
            timeout=30.0,
        )

        self.assertEqual(result, expected_result)

    def test_create_feed(self):
        session = requests.Session()
        expected_result = {"feed_id": 42}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.create_feed("http://example.org/feed", 123)

        session.post.assert_called_once_with(
            "http://localhost/v1/feeds",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("feed_url"), "http://example.org/feed")
        self.assertEqual(payload.get("category_id"), 123)
        self.assertIsNone(payload.get("username"))
        self.assertIsNone(payload.get("password"))
        self.assertIsNone(payload.get("crawler"))
        self.assertEqual(result, expected_result["feed_id"])

    def test_create_feed_with_no_category(self):
        session = requests.Session()
        expected_result = {"feed_id": 42}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.create_feed("http://example.org/feed")

        session.post.assert_called_once_with(
            "http://localhost/v1/feeds",
            data=mock.ANY,
            timeout=30.0,
        )

        _, kwargs = session.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("feed_url"), "http://example.org/feed")
        self.assertIsNone(payload.get("category_id"))
        self.assertIsNone(payload.get("username"))
        self.assertIsNone(payload.get("password"))
        self.assertIsNone(payload.get("crawler"))
        self.assertEqual(result, expected_result["feed_id"])

    def test_create_feed_with_credentials(self):
        session = requests.Session()
        expected_result = {"feed_id": 42}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.create_feed("http://example.org/feed", 123, username="foobar", password="secret")

        session.post.assert_called_once_with(
            "http://localhost/v1/feeds",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("feed_url"), "http://example.org/feed")
        self.assertEqual(payload.get("category_id"), 123)
        self.assertEqual(payload.get("username"), "foobar")
        self.assertEqual(payload.get("password"), "secret")
        self.assertIsNone(payload.get("crawler"))
        self.assertEqual(result, expected_result["feed_id"])

    def test_create_feed_with_crawler_enabled(self):
        session = requests.Session()
        expected_result = {"feed_id": 42}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.create_feed("http://example.org/feed", 123, crawler=True)

        session.post.assert_called_once_with(
            "http://localhost/v1/feeds",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("feed_url"), "http://example.org/feed")
        self.assertEqual(payload.get("category_id"), 123)
        self.assertIsNone(payload.get("username"))
        self.assertIsNone(payload.get("password"))
        self.assertTrue(payload.get("crawler"))
        self.assertEqual(result, expected_result["feed_id"])

    def test_create_feed_with_custom_user_agent_and_crawler_disabled(self):
        session = requests.Session()
        expected_result = {"feed_id": 42}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.create_feed("http://example.org/feed", 123, crawler=False, user_agent="GoogleBot")

        session.post.assert_called_once_with(
            "http://localhost/v1/feeds",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("feed_url"), "http://example.org/feed")
        self.assertEqual(payload.get("category_id"), 123)
        self.assertIsNone(payload.get("username"))
        self.assertIsNone(payload.get("password"))
        self.assertFalse(payload.get("crawler"))
        self.assertEqual(payload.get("user_agent"), "GoogleBot")
        self.assertEqual(result, expected_result["feed_id"])

    def test_update_feed(self):
        session = requests.Session()
        expected_result = {"id": 123, "crawler": True, "username": "test"}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.update_feed(123, crawler=True, username="test")

        session.put.assert_called_once_with(
            "http://localhost/v1/feeds/123",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.put.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertNotIn("feed_url", payload)
        self.assertNotIn("category_id", payload)
        self.assertEqual(payload.get("username"), "test")
        self.assertTrue(payload.get("crawler"))
        self.assertEqual(result, expected_result)

    def test_refresh_all_feeds(self):
        session = requests.Session()
        expected_result = True

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.refresh_all_feeds()

        session.put.assert_called_once_with(
            "http://localhost/v1/feeds/refresh",
            timeout=30,
        )

        assert result == expected_result

    def test_refresh_feed(self):
        session = requests.Session()
        expected_result = True

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.refresh_feed(123)

        session.put.assert_called_once_with(
            "http://localhost/v1/feeds/123/refresh",
            timeout=30,
        )

        assert result == expected_result

    def test_refresh_category(self):
        session = requests.Session()
        expected_result = True

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.refresh_category(123)

        session.put.assert_called_once_with(
            "http://localhost/v1/categories/123/refresh",
            timeout=30,
        )

        assert result == expected_result

    def test_get_feed_entry(self):
        session = requests.Session()
        expected_result = {}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_feed_entry(123, 456)

        session.get.assert_called_once_with(
            "http://localhost/v1/feeds/123/entries/456",
            timeout=30,
        )

        assert result == expected_result

    def test_get_feed_entries(self):
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_feed_entries(123)

        session.get.assert_called_once_with(
            "http://localhost/v1/feeds/123/entries",
            params=None,
            timeout=30,
        )

        assert result == expected_result

    def test_get_feed_entries_with_direction_param(self):
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_feed_entries(123, direction="asc")

        session.get.assert_called_once_with(
            "http://localhost/v1/feeds/123/entries",
            params={"direction": "asc"},
            timeout=30,
        )

        assert result == expected_result

    def test_import_entry(self):
        session = requests.Session()
        expected_result = {"id": 1790}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.import_entry(
            123,
            url="http://example.org/article.html",
            title="Entry Title",
            starred=True,
            tags=["tag1", "tag2"],
        )

        session.post.assert_called_once_with(
            "http://localhost/v1/feeds/123/entries/import",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("url"), "http://example.org/article.html")
        self.assertEqual(payload.get("title"), "Entry Title")
        self.assertTrue(payload.get("starred"))
        self.assertEqual(payload.get("tags"), ["tag1", "tag2"])
        self.assertEqual(result, expected_result)

    def test_import_entry_with_published_at_timestamp(self):
        session = requests.Session()
        expected_result = {"id": 1790}
        published_at = int(time.time())

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.import_entry(
            123,
            url="http://example.org/article.html",
            published_at=published_at,
        )

        session.post.assert_called_once_with(
            "http://localhost/v1/feeds/123/entries/import",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("published_at"), published_at)
        self.assertEqual(result, expected_result)

    def test_import_entry_when_existing(self):
        session = requests.Session()
        expected_result = {"id": 1790}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.import_entry(123, url="http://example.org/article.html")

        session.post.assert_called_once_with(
            "http://localhost/v1/feeds/123/entries/import",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("url"), "http://example.org/article.html")
        self.assertEqual(result, expected_result)

    def test_import_entry_without_url(self):
        session = requests.Session()
        client = miniflux.Client("http://localhost", "username", "password", session=session)

        with self.assertRaises(ValueError):
            client.import_entry(123, url="")

    def test_mark_feed_as_read(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 204

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret", session=session)
        client.mark_feed_entries_as_read(123)

        session.put.assert_called_once_with(
            "http://localhost/v1/feeds/123/mark-all-as-read",
            timeout=30,
        )
        self.assertEqual(session.headers.get("X-Auth-Token"), "secret")

    def test_mark_category_entries_as_read(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 204

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret", session=session)
        client.mark_category_entries_as_read(123)

        session.put.assert_called_once_with(
            "http://localhost/v1/categories/123/mark-all-as-read",
            timeout=30,
        )
        self.assertEqual(session.headers.get("X-Auth-Token"), "secret")

    def test_mark_user_entries_as_read(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 204

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret", session=session)
        client.mark_user_entries_as_read(123)

        session.put.assert_called_once_with(
            "http://localhost/v1/users/123/mark-all-as-read",
            timeout=30,
        )
        self.assertEqual(session.headers.get("X-Auth-Token"), "secret")

    def test_get_entry(self):
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_entry(123)

        session.get.assert_called_once_with(
            "http://localhost/v1/entries/123",
            timeout=30,
        )

        assert result == expected_result

    def test_fetch_entry_content(self):
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.fetch_entry_content(123)

        session.get.assert_called_once_with(
            "http://localhost/v1/entries/123/fetch-content",
            timeout=30,
        )

        assert result == expected_result

    def test_get_entries(self):
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_entries(status="unread", limit=10, offset=5)

        session.get.assert_called_once_with(
            "http://localhost/v1/entries",
            params=mock.ANY,
            timeout=30,
        )

        assert result == expected_result

    def test_get_entries_with_before_param(self):
        param_value = int(time.time())
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_entries(before=param_value)

        session.get.assert_called_once_with(
            "http://localhost/v1/entries",
            params={"before": param_value},
            timeout=30,
        )

        assert result == expected_result

    def test_get_entries_with_starred_param(self):
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_entries(starred=True)

        session.get.assert_called_once_with(
            "http://localhost/v1/entries",
            params={"starred": True},
            timeout=30,
        )

        assert result == expected_result

    def test_get_entries_with_starred_param_at_false(self):
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_entries(starred=False, after_entry_id=123)

        session.get.assert_called_once_with(
            "http://localhost/v1/entries",
            params={"after_entry_id": 123},
            timeout=30,
        )

        assert result == expected_result

    def test_get_user_by_id(self):
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_user_by_id(123)

        session.get.assert_called_once_with(
            "http://localhost/v1/users/123",
            timeout=30,
        )

        assert result == expected_result

    def test_get_inexisting_user(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 404
        response.json.return_value = {"error_message": "some error"}

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)

        with self.assertRaises(ResourceNotFound):
            client.get_user_by_id(123)

    def test_get_user_by_username(self):
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_user_by_username("foobar")

        session.get.assert_called_once_with(
            "http://localhost/v1/users/foobar",
            timeout=30,
        )

        assert result == expected_result

    def test_update_user(self):
        session = requests.Session()
        expected_result = {"id": 123, "theme": "Black", "language": "fr_FR"}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.update_user(123, theme="black", language="fr_FR")

        session.put.assert_called_once_with(
            "http://localhost/v1/users/123",
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = session.put.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertNotIn("username", payload)
        self.assertNotIn("password", payload)
        self.assertEqual(payload.get("theme"), "black")
        self.assertEqual(payload.get("language"), "fr_FR")
        self.assertEqual(result, expected_result)

    def test_timeout(self):
        session = requests.Session()
        session.get = mock.Mock()
        session.get.side_effect = Timeout()

        client = miniflux.Client("http://localhost", "username", "password", 1.0, session=session)
        with self.assertRaises(Timeout):
            client.export()

        session.get.assert_called_once_with(
            "http://localhost/v1/export",
            timeout=1.0,
        )

    def test_api_key_auth(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = {}

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret", session=session)
        client.export()

        session.get.assert_called_once_with(
            "http://localhost/v1/export",
            timeout=30.0,
        )
        self.assertEqual(session.headers.get("X-Auth-Token"), "secret")

    def test_save_entry(self):
        session = requests.Session()
        expected_result = True

        response = mock.Mock()
        response.status_code = 202
        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret", session=session)
        result = client.save_entry(123)

        session.post.assert_called_once_with(
            "http://localhost/v1/entries/123/save",
            timeout=30.0,
        )
        self.assertEqual(session.headers.get("X-Auth-Token"), "secret")
        self.assertEqual(result, expected_result)

    def test_get_category_entry(self):
        session = requests.Session()
        expected_result = {}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_category_entry(123, 456)

        session.get.assert_called_once_with(
            "http://localhost/v1/categories/123/entries/456",
            timeout=30,
        )

        assert result == expected_result

    def test_get_category_entries(self):
        session = requests.Session()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_category_entries(123)

        session.get.assert_called_once_with(
            "http://localhost/v1/categories/123/entries",
            params=None,
            timeout=30,
        )

        assert result == expected_result

    def test_update_entry_title(self):
        session = requests.Session()
        expected_result = {"id": 123, "title": "New title"}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.update_entry(entry_id=123, title="New title")

        session.put.assert_called_once_with(
            "http://localhost/v1/entries/123",
            data=mock.ANY,
            timeout=30.0,
        )

        _, kwargs = session.put.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("title"), "New title")
        self.assertEqual(result, expected_result)

    def test_update_entry_content(self):
        session = requests.Session()
        expected_result = {"id": 123, "content": "New content"}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.update_entry(entry_id=123, content="New content")

        session.put.assert_called_once_with(
            "http://localhost/v1/entries/123",
            data=mock.ANY,
            timeout=30.0,
        )

        _, kwargs = session.put.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("content"), "New content")
        self.assertEqual(result, expected_result)

    def test_update_entries_status(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 204

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.update_entries(entry_ids=[123, 456], status="read")

        session.put.assert_called_once_with(
            "http://localhost/v1/entries",
            data=mock.ANY,
            timeout=30.0,
        )

        _, kwargs = session.put.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("entry_ids"), [123, 456])
        self.assertEqual(payload.get("status"), "read")
        self.assertTrue(result)

    def test_get_enclosure(self):
        session = requests.Session()
        expected_result = {"id": 123, "mime_type": "audio/mpeg"}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_enclosure(123)

        session.get.assert_called_once_with(
            "http://localhost/v1/enclosures/123",
            timeout=30.0,
        )

        self.assertEqual(result, expected_result)

    def test_update_enclosure(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 204

        session.put = mock.Mock()
        session.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        self.assertTrue(client.update_enclosure(123, media_progression=42))

        session.put.assert_called_once_with(
            "http://localhost/v1/enclosures/123",
            data=mock.ANY,
            timeout=30.0,
        )

    def test_get_integrations_status(self):
        session = requests.Session()
        expected_result = {"has_integrations": True}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        result = client.get_integrations_status()

        session.get.assert_called_once_with(
            "http://localhost/v1/integrations/status",
            timeout=30.0,
        )

        self.assertTrue(result)

    def test_get_api_keys(self):
        session = requests.Session()
        expected_result = [{"id": 1, "description": "Test API Key"}]

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret", session=session)
        result = client.get_api_keys()

        session.get.assert_called_once_with(
            "http://localhost/v1/api-keys",
            timeout=30.0,
        )
        self.assertEqual(session.headers.get("X-Auth-Token"), "secret")
        self.assertEqual(result, expected_result)

    def test_create_api_key(self):
        session = requests.Session()
        expected_result = {"id": 2, "description": "New API Key", "token": "some-token"}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        session.post = mock.Mock()
        session.post.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret", session=session)
        result = client.create_api_key("New API Key")

        session.post.assert_called_once_with(
            "http://localhost/v1/api-keys",
            data=json.dumps({"description": "New API Key"}),
            timeout=30.0,
        )
        self.assertEqual(session.headers.get("X-Auth-Token"), "secret")
        self.assertEqual(result, expected_result)

    def test_delete_api_key(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 204

        session.delete = mock.Mock()
        session.delete.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret", session=session)
        client.delete_api_key(1)

        session.delete.assert_called_once_with(
            "http://localhost/v1/api-keys/1",
            timeout=30.0,
        )
        self.assertEqual(session.headers.get("X-Auth-Token"), "secret")

    def test_not_found_response(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 404
        response.json.return_value = {"error_message": "Not found"}

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)

        with self.assertRaises(ResourceNotFound):
            client.get_version()

    def test_unauthorized_response(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 401
        response.json.return_value = {"error_message": "Unauthorized"}

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)

        with self.assertRaises(AccessUnauthorized):
            client.get_version()

    def test_forbidden_response(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 403
        response.json.return_value = {"error_message": "Forbidden"}

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)

        with self.assertRaises(AccessForbidden):
            client.get_version()

    def test_bad_request_response(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 400
        response.json.return_value = {"error_message": "Bad request"}

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)

        with self.assertRaises(BadRequest):
            client.get_version()

    def test_server_error_response(self):
        session = requests.Session()

        response = mock.Mock()
        response.status_code = 500
        response.json.return_value = {"error_message": "Server error"}

        session.get = mock.Mock()
        session.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password", session=session)

        with self.assertRaises(ServerError):
            client.get_version()

    def test_session_closed(self):
        session = mock.Mock()

        client = miniflux.Client("http://localhost", "username", "password", session=session)
        client.close()

        session.close.assert_called()

    def test_context_manager_exit_on_error(self):
        response = mock.Mock()
        response.status_code = 500
        response.json.return_value = {"error_message": "Server error"}

        session = mock.Mock()
        session.get.return_value = response

        with miniflux.Client("http://localhost", "username", "password", session=session) as client:
            with self.assertRaises(ServerError):
                client.get_version()

        session.close.assert_called()
