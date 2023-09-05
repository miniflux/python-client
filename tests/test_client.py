# The MIT License (MIT)
#
# Copyright (c) 2018-2022 Frederic Guillot
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
from miniflux import ClientError
from requests.exceptions import Timeout


class TestMinifluxClient(unittest.TestCase):
    def test_get_error_reason(self):
        response = mock.Mock()
        response.status_code = 404
        response.json.return_value = {"error_message": "some error"}
        error = ClientError(response)
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.get_error_reason(), "some error")

    def test_get_error_without_reason(self):
        response = mock.Mock()
        response.status_code = 404
        response.json.return_value = {}
        error = ClientError(response)
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.get_error_reason(), "status_code=404")

    def test_get_error_with_bad_response(self):
        response = mock.Mock()
        response.status_code = 404
        response.json.return_value = None
        error = ClientError(response)
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.get_error_reason(), "status_code=404")

    def test_base_url_with_trailing_slash(self):
        requests = _get_request_mock()
        expected_result = [
            {"url": "http://example.org/feed", "title": "Example", "type": "RSS"}
        ]

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.post.return_value = response

        client = miniflux.Client("http://localhost/", "username", "password")
        result = client.discover("http://example.org/")

        requests.post.assert_called_once_with(
            "http://localhost/v1/discover",
            headers=None,
            auth=("username", "password"),
            data=mock.ANY,
            timeout=30,
        )

        self.assertEqual(result, expected_result)

    def test_get_me(self):
        requests = _get_request_mock()
        expected_result = {"id": 123, "username": "foobar"}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.me()

        requests.get.assert_called_once_with(
            "http://localhost/v1/me",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        self.assertEqual(result, expected_result)

    def test_get_me_with_server_error(self):
        requests = _get_request_mock()

        response = mock.Mock()
        response.status_code = 500

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")

        with self.assertRaises(ClientError):
            client.me()

    def test_discover(self):
        requests = _get_request_mock()
        expected_result = [
            {"url": "http://example.org/feed", "title": "Example", "type": "RSS"}
        ]

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.discover("http://example.org/")

        requests.post.assert_called_once_with(
            "http://localhost/v1/discover",
            headers=None,
            auth=("username", "password"),
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = requests.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("url"), "http://example.org/")
        self.assertIsNone(payload.get("username"))
        self.assertIsNone(payload.get("password"))
        self.assertEqual(result, expected_result)

    def test_discover_with_credentials(self):
        requests = _get_request_mock()
        expected_result = [
            {"url": "http://example.org/feed", "title": "Example", "type": "RSS"}
        ]

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.discover(
            "http://example.org/",
            username="foobar",
            password="secret",
            user_agent="Bot",
        )

        requests.post.assert_called_once_with(
            "http://localhost/v1/discover",
            headers=None,
            auth=("username", "password"),
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = requests.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("url"), "http://example.org/")
        self.assertEqual(payload.get("username"), "foobar")
        self.assertEqual(payload.get("password"), "secret")
        self.assertEqual(payload.get("user_agent"), "Bot")
        self.assertEqual(result, expected_result)

    def test_discover_with_server_error(self):
        requests = _get_request_mock()
        expected_result = {"error_message": "some error"}

        response = mock.Mock()
        response.status_code = 500
        response.json.return_value = expected_result

        requests.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")

        with self.assertRaises(ClientError):
            client.discover("http://example.org/")

    def test_export(self):
        requests = _get_request_mock()
        expected_result = "OPML feed"

        response = mock.Mock()
        response.status_code = 200
        response.text = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.export()

        requests.get.assert_called_once_with(
            "http://localhost/v1/export",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        self.assertEqual(result, expected_result)

    def test_import(self):
        requests = _get_request_mock()
        input_data = "my opml data"

        response = mock.Mock()
        response.status_code = 201

        requests.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        client.import_feeds(input_data)

        requests.post.assert_called_once_with(
            "http://localhost/v1/import",
            headers=None,
            data=input_data,
            auth=("username", "password"),
            timeout=30,
        )

    def test_import_failure(self):
        requests = _get_request_mock()
        input_data = "my opml data"

        response = mock.Mock()
        response.status_code = 500
        response.json.return_value = {"error_message": "random error"}

        requests.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")

        with self.assertRaises(ClientError):
            client.import_feeds(input_data)

        requests.post.assert_called_once_with(
            "http://localhost/v1/import",
            headers=None,
            data=input_data,
            auth=("username", "password"),
            timeout=30,
        )

    def test_get_feed(self):
        requests = _get_request_mock()
        expected_result = {"id": 123, "title": "Example"}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_feed(123)

        requests.get.assert_called_once_with(
            "http://localhost/v1/feeds/123",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        self.assertEqual(result, expected_result)

    def test_create_feed(self):
        requests = _get_request_mock()
        expected_result = {"feed_id": 42}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        requests.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.create_feed("http://example.org/feed", 123)

        requests.post.assert_called_once_with(
            "http://localhost/v1/feeds",
            headers=None,
            auth=("username", "password"),
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = requests.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("feed_url"), "http://example.org/feed")
        self.assertEqual(payload.get("category_id"), 123)
        self.assertIsNone(payload.get("username"))
        self.assertIsNone(payload.get("password"))
        self.assertIsNone(payload.get("crawler"))
        self.assertEqual(result, expected_result["feed_id"])

    def test_create_feed_with_credentials(self):
        requests = _get_request_mock()
        expected_result = {"feed_id": 42}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        requests.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.create_feed(
            "http://example.org/feed", 123, username="foobar", password="secret"
        )

        requests.post.assert_called_once_with(
            "http://localhost/v1/feeds",
            headers=None,
            auth=("username", "password"),
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = requests.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("feed_url"), "http://example.org/feed")
        self.assertEqual(payload.get("category_id"), 123)
        self.assertEqual(payload.get("username"), "foobar")
        self.assertEqual(payload.get("password"), "secret")
        self.assertIsNone(payload.get("crawler"))
        self.assertEqual(result, expected_result["feed_id"])

    def test_create_feed_with_crawler_enabled(self):
        requests = _get_request_mock()
        expected_result = {"feed_id": 42}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        requests.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.create_feed("http://example.org/feed", 123, crawler=True)

        requests.post.assert_called_once_with(
            "http://localhost/v1/feeds",
            headers=None,
            auth=("username", "password"),
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = requests.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("feed_url"), "http://example.org/feed")
        self.assertEqual(payload.get("category_id"), 123)
        self.assertIsNone(payload.get("username"))
        self.assertIsNone(payload.get("password"))
        self.assertTrue(payload.get("crawler"))
        self.assertEqual(result, expected_result["feed_id"])

    def test_create_feed_with_custom_user_agent_and_crawler_disabled(self):
        requests = _get_request_mock()
        expected_result = {"feed_id": 42}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        requests.post.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.create_feed(
            "http://example.org/feed", 123, crawler=False, user_agent="GoogleBot"
        )

        requests.post.assert_called_once_with(
            "http://localhost/v1/feeds",
            headers=None,
            auth=("username", "password"),
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = requests.post.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertEqual(payload.get("feed_url"), "http://example.org/feed")
        self.assertEqual(payload.get("category_id"), 123)
        self.assertIsNone(payload.get("username"))
        self.assertIsNone(payload.get("password"))
        self.assertFalse(payload.get("crawler"))
        self.assertEqual(payload.get("user_agent"), "GoogleBot")
        self.assertEqual(result, expected_result["feed_id"])

    def test_update_feed(self):
        requests = _get_request_mock()
        expected_result = {"id": 123, "crawler": True, "username": "test"}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        requests.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.update_feed(123, crawler=True, username="test")

        requests.put.assert_called_once_with(
            "http://localhost/v1/feeds/123",
            headers=None,
            auth=("username", "password"),
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = requests.put.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertNotIn("feed_url", payload)
        self.assertNotIn("category_id", payload)
        self.assertEqual(payload.get("username"), "test")
        self.assertTrue(payload.get("crawler"))
        self.assertEqual(result, expected_result)

    def test_refresh_all_feeds(self):
        requests = _get_request_mock()
        expected_result = True

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        requests.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.refresh_all_feeds()

        requests.put.assert_called_once_with(
            "http://localhost/v1/feeds/refresh",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        assert result == expected_result

    def test_refresh_feed(self):
        requests = _get_request_mock()
        expected_result = True

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        requests.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.refresh_feed(123)

        requests.put.assert_called_once_with(
            "http://localhost/v1/feeds/123/refresh",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        assert result == expected_result

    def test_refresh_category(self):
        requests = _get_request_mock()
        expected_result = True

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        requests.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.refresh_category(123)

        requests.put.assert_called_once_with(
            "http://localhost/v1/categories/123/refresh",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        assert result == expected_result

    def test_get_feed_entry(self):
        requests = _get_request_mock()
        expected_result = {}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_feed_entry(123, 456)

        requests.get.assert_called_once_with(
            "http://localhost/v1/feeds/123/entries/456",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        assert result == expected_result

    def test_get_feed_entries(self):
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_feed_entries(123)

        requests.get.assert_called_once_with(
            "http://localhost/v1/feeds/123/entries",
            headers=None,
            auth=("username", "password"),
            params=None,
            timeout=30,
        )

        assert result == expected_result

    def test_get_feed_entries_with_direction_param(self):
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_feed_entries(123, direction="asc")

        requests.get.assert_called_once_with(
            "http://localhost/v1/feeds/123/entries",
            headers=None,
            auth=("username", "password"),
            params={"direction": "asc"},
            timeout=30,
        )

        assert result == expected_result

    def test_mark_feed_as_read(self):
        requests = _get_request_mock()

        response = mock.Mock()
        response.status_code = 204

        requests.put.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret")
        client.mark_feed_entries_as_read(123)

        requests.put.assert_called_once_with(
            "http://localhost/v1/feeds/123/mark-all-as-read",
            headers={"X-Auth-Token": "secret"},
            auth=None,
            timeout=30,
        )

    def test_mark_category_entries_as_read(self):
        requests = _get_request_mock()

        response = mock.Mock()
        response.status_code = 204

        requests.put.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret")
        client.mark_category_entries_as_read(123)

        requests.put.assert_called_once_with(
            "http://localhost/v1/categories/123/mark-all-as-read",
            headers={"X-Auth-Token": "secret"},
            auth=None,
            timeout=30,
        )

    def test_mark_user_entries_as_read(self):
        requests = _get_request_mock()

        response = mock.Mock()
        response.status_code = 204

        requests.put.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret")
        client.mark_user_entries_as_read(123)

        requests.put.assert_called_once_with(
            "http://localhost/v1/users/123/mark-all-as-read",
            headers={"X-Auth-Token": "secret"},
            auth=None,
            timeout=30,
        )

    def test_get_entry(self):
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_entry(123)

        requests.get.assert_called_once_with(
            "http://localhost/v1/entries/123",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        assert result == expected_result

    def test_fetch_entry_content(self):
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.fetch_entry_content(123)

        requests.get.assert_called_once_with(
            "http://localhost/v1/entries/123/fetch-content",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        assert result == expected_result

    def test_get_entries(self):
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_entries(status="unread", limit=10, offset=5)

        requests.get.assert_called_once_with(
            "http://localhost/v1/entries",
            headers=None,
            auth=("username", "password"),
            params=mock.ANY,
            timeout=30,
        )

        assert result == expected_result

    def test_get_entries_with_before_param(self):
        param_value = int(time.time())
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_entries(before=param_value)

        requests.get.assert_called_once_with(
            "http://localhost/v1/entries",
            headers=None,
            auth=("username", "password"),
            params={"before": param_value},
            timeout=30,
        )

        assert result == expected_result

    def test_get_entries_with_starred_param(self):
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_entries(starred=True)

        requests.get.assert_called_once_with(
            "http://localhost/v1/entries",
            headers=None,
            auth=("username", "password"),
            params={"starred": True},
            timeout=30,
        )

        assert result == expected_result

    def test_get_entries_with_starred_param_at_false(self):
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_entries(starred=False, after_entry_id=123)

        requests.get.assert_called_once_with(
            "http://localhost/v1/entries",
            headers=None,
            auth=("username", "password"),
            params={"after_entry_id": 123},
            timeout=30,
        )

        assert result == expected_result

    def test_get_user_by_id(self):
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_user_by_id(123)

        requests.get.assert_called_once_with(
            "http://localhost/v1/users/123",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        assert result == expected_result

    def test_get_user_by_username(self):
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_user_by_username("foobar")

        requests.get.assert_called_once_with(
            "http://localhost/v1/users/foobar",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        assert result == expected_result

    def test_update_user(self):
        requests = _get_request_mock()
        expected_result = {"id": 123, "theme": "Black", "language": "fr_FR"}

        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = expected_result

        requests.put.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.update_user(123, theme="black", language="fr_FR")

        requests.put.assert_called_once_with(
            "http://localhost/v1/users/123",
            headers=None,
            auth=("username", "password"),
            data=mock.ANY,
            timeout=30,
        )

        _, kwargs = requests.put.call_args
        payload = json.loads(kwargs.get("data"))

        self.assertNotIn("username", payload)
        self.assertNotIn("password", payload)
        self.assertEqual(payload.get("theme"), "black")
        self.assertEqual(payload.get("language"), "fr_FR")
        self.assertEqual(result, expected_result)

    def test_timeout(self):
        requests = _get_request_mock()
        requests.get.side_effect = Timeout()

        client = miniflux.Client("http://localhost", "username", "password", 1.0)
        with self.assertRaises(Timeout):
            client.export()

        requests.get.assert_called_once_with(
            "http://localhost/v1/export",
            headers=None,
            auth=("username", "password"),
            timeout=1.0,
        )

    def test_api_key_auth(self):
        requests = _get_request_mock()

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = {}

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret")
        client.export()

        requests.get.assert_called_once_with(
            "http://localhost/v1/export",
            headers={"X-Auth-Token": "secret"},
            auth=None,
            timeout=30.0,
        )

    def test_save_entry(self):
        requests = _get_request_mock()
        expected_result = True

        response = mock.Mock()
        response.status_code = 202
        requests.post.return_value = response

        client = miniflux.Client("http://localhost", api_key="secret")
        result = client.save_entry(123)

        requests.post.assert_called_once_with(
            "http://localhost/v1/entries/123/save",
            headers={"X-Auth-Token": "secret"},
            auth=None,
            timeout=30.0,
        )
        assert result == expected_result

    def test_get_category_entry(self):
        requests = _get_request_mock()
        expected_result = {}

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_category_entry(123, 456)

        requests.get.assert_called_once_with(
            "http://localhost/v1/categories/123/entries/456",
            headers=None,
            auth=("username", "password"),
            timeout=30,
        )

        assert result == expected_result

    def test_get_category_entries(self):
        requests = _get_request_mock()
        expected_result = []

        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = expected_result

        requests.get.return_value = response

        client = miniflux.Client("http://localhost", "username", "password")
        result = client.get_category_entries(123)

        requests.get.assert_called_once_with(
            "http://localhost/v1/categories/123/entries",
            headers=None,
            auth=("username", "password"),
            params=None,
            timeout=30,
        )

        assert result == expected_result


def _get_request_mock():
    patcher = mock.patch("miniflux.requests")
    return patcher.start()
