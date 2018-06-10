# The MIT License (MIT)
#
# Copyright (c) 2018 Frederic Guillot
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

import time
from unittest import mock

import pytest

import miniflux
from miniflux import ClientError

from requests.exceptions import Timeout


def test_get_error_reason():
    response = mock.Mock()
    response.status_code = 404
    response.json.return_value = {'error_message': 'some error'}
    error = ClientError(response)
    assert error.status_code == 404
    assert error.get_error_reason() == 'some error'


def test_get_error_without_reason():
    response = mock.Mock()
    response.status_code = 404
    response.json.return_value = {}
    error = ClientError(response)
    assert error.status_code == 404
    assert error.get_error_reason() == 'status_code=404'


def test_get_error_with_bad_response():
    response = mock.Mock()
    response.status_code = 404
    response.json.return_value = None
    error = ClientError(response)
    assert error.status_code == 404
    assert error.get_error_reason() == 'status_code=404'


def test_base_url_with_trailing_slash():
    requests = _get_request_mock()
    expected_result = [{"url": "http://example.org/feed", "title": "Example", "type": "RSS"}]

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.post.return_value = response

    client = miniflux.Client("http://localhost/", "username", "password")
    result = client.discover("http://example.org/")

    requests.post.assert_called_once_with('http://localhost/v1/discover',
                                          auth=('username', 'password'),
                                          data='{"url": "http://example.org/"}',
                                          timeout=mock.ANY)

    assert result == expected_result


def test_get_me():
    requests = _get_request_mock()
    expected_result = {"id": 123, "username": "foobar"}

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.me()

    requests.get.assert_called_once_with('http://localhost/v1/me',
                                         auth=('username', 'password'),
                                         timeout=mock.ANY)

    assert result == expected_result


def test_get_me_with_server_error():
    requests = _get_request_mock()

    response = mock.Mock()
    response.status_code = 500

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")

    with pytest.raises(ClientError):
        client.me()


def test_discover():
    requests = _get_request_mock()
    expected_result = [{"url": "http://example.org/feed", "title": "Example", "type": "RSS"}]

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.post.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.discover("http://example.org/")

    requests.post.assert_called_once_with('http://localhost/v1/discover',
                                          auth=('username', 'password'),
                                          data='{"url": "http://example.org/"}',
                                          timeout=mock.ANY)

    assert result == expected_result


def test_discover_with_server_error():
    requests = _get_request_mock()
    expected_result = {'error_message': 'some error'}

    response = mock.Mock()
    response.status_code = 500
    response.json.return_value = expected_result

    requests.post.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")

    with pytest.raises(ClientError):
        client.discover("http://example.org/")


def test_export():
    requests = _get_request_mock()
    expected_result = "OPML feed"

    response = mock.Mock()
    response.status_code = 200
    response.text = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.export()

    requests.get.assert_called_once_with('http://localhost/v1/export',
                                         auth=('username', 'password'),
                                         timeout=mock.ANY)

    assert result == expected_result


def test_import():
    requests = _get_request_mock()
    input_data = "my opml data"

    response = mock.Mock()
    response.status_code = 201

    requests.post.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    client.import_feeds(input_data)

    requests.post.assert_called_once_with('http://localhost/v1/import',
                                          data=input_data,
                                          auth=('username', 'password'),
                                          timeout=mock.ANY)


def test_import_failure():
    requests = _get_request_mock()
    input_data = "my opml data"

    response = mock.Mock()
    response.status_code = 500
    response.json.return_value = {"error_message": "random error"}

    requests.post.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")

    with pytest.raises(ClientError):
        client.import_feeds(input_data)

    requests.post.assert_called_once_with('http://localhost/v1/import',
                                          data=input_data,
                                          auth=('username', 'password'),
                                          timeout=mock.ANY)


def test_get_feed():
    requests = _get_request_mock()
    expected_result = {"id": 123, "title": "Example"}

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.get_feed(123)

    requests.get.assert_called_once_with('http://localhost/v1/feeds/123',
                                         auth=('username', 'password'),
                                         timeout=mock.ANY)

    assert result == expected_result


def test_create_feed():
    requests = _get_request_mock()
    expected_result = {"feed_id": 42}

    response = mock.Mock()
    response.status_code = 201
    response.json.return_value = expected_result

    requests.post.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.create_feed("http://example.org/feed", 123)

    requests.post.assert_called_once_with('http://localhost/v1/feeds',
                                          auth=('username', 'password'),
                                          data=mock.ANY,
                                          timeout=mock.ANY)

    assert result == expected_result['feed_id']


def test_refresh_feed():
    requests = _get_request_mock()
    expected_result = True

    response = mock.Mock()
    response.status_code = 201
    response.json.return_value = expected_result

    requests.put.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.refresh_feed(123)

    requests.put.assert_called_once_with('http://localhost/v1/feeds/123/refresh',
                                         auth=('username', 'password'),
                                         timeout=mock.ANY)

    assert result == expected_result


def test_get_feed_entries():
    requests = _get_request_mock()
    expected_result = []

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.get_feed_entries(123)

    requests.get.assert_called_once_with('http://localhost/v1/feeds/123/entries',
                                         auth=('username', 'password'),
                                         params=None,
                                         timeout=mock.ANY)

    assert result == expected_result


def test_get_feed_entries_with_direction_param():
    requests = _get_request_mock()
    expected_result = []

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.get_feed_entries(123, direction='asc')

    requests.get.assert_called_once_with('http://localhost/v1/feeds/123/entries',
                                         auth=('username', 'password'),
                                         params={'direction': 'asc'},
                                         timeout=mock.ANY)

    assert result == expected_result


def test_get_entry():
    requests = _get_request_mock()
    expected_result = []

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.get_entry(123)

    requests.get.assert_called_once_with('http://localhost/v1/entries/123',
                                         auth=('username', 'password'),
                                         timeout=mock.ANY)

    assert result == expected_result


def test_get_entries():
    requests = _get_request_mock()
    expected_result = []

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.get_entries(status='unread', limit=10, offset=5)

    requests.get.assert_called_once_with('http://localhost/v1/entries',
                                         auth=('username', 'password'),
                                         params=mock.ANY,
                                         timeout=mock.ANY)

    assert result == expected_result


def test_get_entries_with_before_param():
    param_value = int(time.time())
    requests = _get_request_mock()
    expected_result = []

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.get_entries(before=param_value)

    requests.get.assert_called_once_with('http://localhost/v1/entries',
                                         auth=('username', 'password'),
                                         params={'before': param_value},
                                         timeout=mock.ANY)

    assert result == expected_result


def test_get_entries_with_starred_param():
    requests = _get_request_mock()
    expected_result = []

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.get_entries(starred=True)

    requests.get.assert_called_once_with('http://localhost/v1/entries',
                                         auth=('username', 'password'),
                                         params={'starred': True},
                                         timeout=mock.ANY)

    assert result == expected_result


def test_get_entries_with_starred_param_at_false():
    requests = _get_request_mock()
    expected_result = []

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.get_entries(starred=False, after_entry_id=123)

    requests.get.assert_called_once_with('http://localhost/v1/entries',
                                         auth=('username', 'password'),
                                         params={'after_entry_id': 123},
                                         timeout=mock.ANY)

    assert result == expected_result


def test_get_user_by_id():
    requests = _get_request_mock()
    expected_result = []

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.get_user_by_id(123)

    requests.get.assert_called_once_with('http://localhost/v1/users/123',
                                         auth=('username', 'password'),
                                         timeout=mock.ANY)

    assert result == expected_result


def test_get_user_by_username():
    requests = _get_request_mock()
    expected_result = []

    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = expected_result

    requests.get.return_value = response

    client = miniflux.Client("http://localhost", "username", "password")
    result = client.get_user_by_username("foobar")

    requests.get.assert_called_once_with('http://localhost/v1/users/foobar',
                                         auth=('username', 'password'),
                                         timeout=mock.ANY)

    assert result == expected_result


def test_timeout():
    requests = _get_request_mock()
    requests.get.side_effect = Timeout()

    client = miniflux.Client("http://localhost", "username", "password", 1)
    with pytest.raises(Timeout):
        client.export()

    requests.get.assert_called_once_with('http://localhost/v1/export',
                                         auth=('username', 'password'),
                                         timeout=1)


def _get_request_mock():
    patcher = mock.patch('miniflux.requests')
    return patcher.start()
