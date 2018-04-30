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

import json
import requests


class ClientError(Exception):
    def __init__(self, response):
        self.status_code = response.status_code
        self._response = response

    def get_error_reason(self):
        result = self._response.json()
        default_reason = 'status_code={}'.format(self.status_code)
        return result.get('error_message', default_reason) if isinstance(result, dict) else default_reason


class Client:
    API_VERSION = 1

    def __init__(self, base_url, username, password, timeout=None):
        self._base_url = base_url
        self._username = username
        self._password = password
        self._timeout = timeout
        self._auth = (self._username, self._password)

    def _get_endpoint(self, path):
        if len(self._base_url) > 0 and self._base_url[-1:] == '/':
            self._base_url = self._base_url[:-1]

        return '{}/v{}{}'.format(self._base_url, self.API_VERSION, path)

    def _get_params(self, status, offset, limit, order, direction):
        params = {}

        if status:
            params['status'] = status

        if offset:
            params['offset'] = offset

        if limit:
            params['limit'] = limit

        if order:
            params['order'] = order

        if direction:
            params['direction'] = direction

        return params if len(params) > 0 else None

    def export(self):
        return self.export_feeds()

    def export_feeds(self):
        endpoint = self._get_endpoint('/export')
        response = requests.get(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code == 200:
            return response.text
        raise ClientError(response)

    def import_feeds(self, opml):
        endpoint = self._get_endpoint('/import')
        response = requests.post(endpoint, data=opml, auth=self._auth, timeout=self._timeout)
        if response.status_code == 201:
            return response.json()
        raise ClientError(response)

    def discover(self, website_url):
        endpoint = self._get_endpoint('/discover')
        data = {'url': website_url}
        response = requests.post(endpoint, auth=self._auth, data=json.dumps(data), timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def get_feeds(self):
        endpoint = self._get_endpoint('/feeds')
        response = requests.get(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def get_feed(self, feed_id):
        endpoint = self._get_endpoint('/feeds/{}'.format(feed_id))
        response = requests.get(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def get_feed_icon(self, feed_id):
        endpoint = self._get_endpoint('/feeds/{}/icon'.format(feed_id))
        response = requests.get(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def create_feed(self, feed_url, category_id):
        endpoint = self._get_endpoint('/feeds')
        data = {'feed_url': feed_url, 'category_id': category_id}
        response = requests.post(endpoint, auth=self._auth, data=json.dumps(data), timeout=self._timeout)
        if response.status_code == 201:
            return response.json()['feed_id']
        raise ClientError(response)

    def update_feed(self, feed_id, title=None, feed_url=None, site_url=None, scraper_rules=None, rewrite_rules=None,
                    crawler=None, category_id=None):
        endpoint = self._get_endpoint('/feeds/{}'.format(feed_id))
        data = {}

        if title:
            data['title'] = title

        if feed_url:
            data['feed_url'] = feed_url

        if site_url:
            data['site_url'] = site_url

        if scraper_rules:
            data['scraper_rules'] = scraper_rules

        if rewrite_rules:
            data['rewrite_rules'] = rewrite_rules

        if crawler is not None:
            data['crawler'] = crawler

        if category_id:
            data['category'] = {'id': category_id}

        response = requests.put(endpoint, auth=self._auth, data=json.dumps(data), timeout=self._timeout)
        if response.status_code == 201:
            return response.json()
        raise ClientError(response)

    def refresh_feed(self, feed_id):
        endpoint = self._get_endpoint('/feeds/{}/refresh'.format(feed_id))
        response = requests.put(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code >= 400:
            raise ClientError(response)
        return True

    def delete_feed(self, feed_id):
        endpoint = self._get_endpoint('/feeds/{}'.format(feed_id))
        response = requests.delete(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code != 204:
            raise ClientError(response)

    def get_feed_entry(self, feed_id, entry_id):
        endpoint = self._get_endpoint('/feeds/{}/entries/{}'.format(feed_id, entry_id))
        response = requests.get(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def get_feed_entries(self, feed_id, status=None, offset=None, limit=None, order=None, direction=None):
        endpoint = self._get_endpoint('/feeds/{}/entries'.format(feed_id))
        params = self._get_params(status, offset, limit, order, direction)
        response = requests.get(endpoint, auth=self._auth, params=params, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def get_entry(self, entry_id):
        endpoint = self._get_endpoint('/entries/{}'.format(entry_id))
        response = requests.get(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def get_entries(self, status=None, offset=None, limit=None, order=None, direction=None):
        endpoint = self._get_endpoint('/entries')
        params = self._get_params(status, offset, limit, order, direction)
        response = requests.get(endpoint, auth=self._auth, params=params, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def update_entries(self, entry_ids, status):
        endpoint = self._get_endpoint('/entries')
        data = {'entry_ids': entry_ids, 'status': status}
        response = requests.put(endpoint, auth=self._auth, data=json.dumps(data), timeout=self._timeout)
        if response.status_code >= 400:
            raise ClientError(response)
        return True

    def toggle_bookmark(self, entry_id):
        endpoint = self._get_endpoint('/entries/{}/bookmark'.format(entry_id))
        response = requests.put(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code >= 400:
            raise ClientError(response)
        return True

    def get_categories(self):
        endpoint = self._get_endpoint('/categories')
        response = requests.get(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def create_category(self, title):
        endpoint = self._get_endpoint('/categories')
        data = {'title': title}
        response = requests.post(endpoint, auth=self._auth, data=json.dumps(data), timeout=self._timeout)
        if response.status_code == 201:
            return response.json()
        raise ClientError(response)

    def update_category(self, category_id, title):
        endpoint = self._get_endpoint('/categories/{}'.format(category_id))
        data = {'id': category_id, 'title': title}
        response = requests.put(endpoint, auth=self._auth, data=json.dumps(data), timeout=self._timeout)
        if response.status_code == 201:
            return response.json()
        raise ClientError(response)

    def delete_category(self, category_id):
        endpoint = self._get_endpoint('/categories/{}'.format(category_id))
        response = requests.delete(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code != 204:
            raise ClientError(response)

    def get_users(self):
        endpoint = self._get_endpoint('/users')
        response = requests.get(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def get_user_by_id(self, user_id):
        return self._get_user(user_id)

    def get_user_by_username(self, username):
        return self._get_user(username)

    def _get_user(self, user_id_or_username):
        endpoint = self._get_endpoint('/users/{}'.format(user_id_or_username))
        response = requests.get(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        raise ClientError(response)

    def create_user(self, username, password, is_admin):
        endpoint = self._get_endpoint('/users')
        data = {'username': username, 'password': password, 'is_admin': is_admin}
        response = requests.post(endpoint, auth=self._auth, data=json.dumps(data), timeout=self._timeout)
        if response.status_code == 201:
            return response.json()
        raise ClientError(response)

    def update_user(self, user_id, username=None, password=None, theme=None, language=None,
                    timezone=None, entry_direction=None):
        endpoint = self._get_endpoint('/users/{}'.format(user_id))
        data = {}

        if username:
            data['username'] = username

        if password:
            data['password'] = password

        if theme:
            data['theme'] = theme

        if language:
            data['language'] = language

        if timezone:
            data['timezone'] = timezone

        if entry_direction:
            data['entry_direction'] = entry_direction

        response = requests.put(endpoint, auth=self._auth, data=json.dumps(data), timeout=self._timeout)
        if response.status_code == 201:
            return response.json()
        raise ClientError(response)

    def delete_user(self, user_id):
        endpoint = self._get_endpoint('/users/{}'.format(user_id))
        response = requests.delete(endpoint, auth=self._auth, timeout=self._timeout)
        if response.status_code != 204:
            raise ClientError(response)
