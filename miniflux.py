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
from typing import List, Optional, Union

import requests


DEFAULT_USER_AGENT = "Miniflux Python Client Library"


class ClientError(Exception):
    """
    Exception raised when the API client receives an error response from the server.

    Attributes:
        status_code (int): The HTTP status code of the error response.
    """

    def __init__(self, response: requests.Response):
        self.status_code = response.status_code
        self._response = response

    def get_error_reason(self) -> str:
        """
        Returns the error message from the response body, or a default message if not available.

        Returns:
            str: The error message from the response body, or a default message if not available.
        """
        default_reason = f"status_code={self.status_code}"
        if self._response.headers.get("Content-Type") == "application/json":
            result = self._response.json()
            if isinstance(result, dict):
                return result.get("error_message", default_reason)
        return default_reason


class ResourceNotFound(ClientError):
    """
    Exception raised when the API client receives a 404 response from the server.
    """

    pass


class AccessForbidden(ClientError):
    """
    Exception raised when the API client receives a 403 response from the server.
    """

    pass


class AccessUnauthorized(ClientError):
    """
    Exception raised when the API client receives a 401 response from the server.
    """

    pass


class BadRequest(ClientError):
    """
    Exception raised when the API client receives a 400 response from the server.
    """

    pass


class ServerError(ClientError):
    """
    Exception raised when the API client receives a 500 response from the server.
    """

    pass


class Client:
    """
    Miniflux API client.
    """

    API_VERSION = 1

    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 30.0,
        api_key: Optional[str] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        session: Optional[requests.Session] = None,
    ):
        """
        Initializes the Miniflux API client.

        Args:
            base_url (str): The base URL of the Miniflux API. Must start with "http://" or "https://".
            username (Optional[str]): The username for basic authentication.
                                      Required if `api_key` is not provided.
            password (Optional[str]): The password for basic authentication.
                                      Required if `api_key` is not provided.
            timeout (float): The timeout for API requests in seconds. Default is 30.0 seconds.
            api_key (Optional[str]): The API key for authentication.
                                     If provided, takes precedence over `username` and `password`.
            user_agent (str): The User-Agent string to use for API requests.
                              Default is "Miniflux Python Client Library".
            session (requests.Session): A custom requests session to use for API requests.

        Raises:
            ValueError: If `base_url` is not a valid URL starting with "http://" or "https://".
            ValueError: If neither `api_key` nor both `username` and `password` are provided.
        """
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must be a valid URL starting with http:// or https://")

        if not api_key and not (username and password):
            raise ValueError("Either api_key or both username and password must be provided")

        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = session or requests.Session()

        self._session.headers.update({"User-Agent": user_agent})
        if api_key:
            self._session.headers.update({"X-Auth-Token": api_key})
        elif username and password:
            self._session.auth = (username, password)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get_endpoint(self, path: str) -> str:
        return f"{self._base_url}/v{self.API_VERSION}{path}"

    def _get_params(self, **kwargs) -> Optional[dict]:
        params = {k: v for k, v in kwargs.items() if v}
        return params if len(params) > 0 else None

    def _get_modification_params(self, **kwargs) -> dict:
        return {k: v for k, v in kwargs.items() if v is not None}

    def _handle_error_response(self, response: requests.Response):
        if response.status_code == 404:
            raise ResourceNotFound(response)
        if response.status_code == 403:
            raise AccessForbidden(response)
        if response.status_code == 401:
            raise AccessUnauthorized(response)
        if response.status_code == 400:
            raise BadRequest(response)
        if response.status_code >= 500:
            raise ServerError(response)
        raise ClientError(response)

    def flush_history(self) -> bool:
        """
        Mark all read entries as removed excepted the starred ones.

        Returns:
            bool: True if the operation was successfully scheduled, False otherwise.
        """
        endpoint = self._get_endpoint("/flush-history")
        response = self._session.delete(endpoint, timeout=self._timeout)
        if response.status_code == 202:
            return True
        self._handle_error_response(response)

    def get_version(self) -> dict:
        """
        Get the version information of the Miniflux instance.

        Returns:
            A dictionary containing the version information.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/version")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def me(self) -> dict:
        """
        Get the authenticated user's information.

        Returns:
            A dictionary containing the user's information.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/me")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def export(self) -> str:
        """
        Export the user's feeds in OPML format.

        Returns:
            str: The OPML data.
        Raises:
            ClientError: If the request fails.
        """
        return self.export_feeds()

    def export_feeds(self) -> str:
        """
        Export the user's feeds in OPML format.

        Returns:
            str: The OPML data.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/export")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.text
        self._handle_error_response(response)

    def import_feeds(self, opml: str) -> dict:
        """
        Import feeds from an OPML file.

        Args:
            opml (str): The OPML data.
        Returns:
            A dictionary containing the import result.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/import")
        response = self._session.post(
            endpoint,
            data=opml,
            timeout=self._timeout,
        )
        if response.status_code == 201:
            return response.json()
        self._handle_error_response(response)

    def discover(self, website_url: str, **kwargs) -> List[dict]:
        """
        Discover feeds from a website.

        Args:
            website_url (str): The website URL.
        Returns:
            List of feeds.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/discover")
        data = dict(url=website_url)
        data.update(kwargs)

        response = self._session.post(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_category_feeds(self, category_id: int) -> List[dict]:
        """
        Retrieves a list of feeds for a given category.

        Args:
            category_id (int): The category ID.
        Returns:
            A list of dictionaries representing the feeds.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/categories/{category_id}/feeds")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_feeds(self) -> List[dict]:
        """
        Retrieves a list of all feeds.

        Returns:
            A list of dictionaries representing the feeds.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/feeds")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_feed(self, feed_id: int) -> dict:
        """
        Retrieves a feed.

        Args:
            feed_id (int): The feed ID.
        Returns:
            A dictionary representing the feed.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/feeds/{feed_id}")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_feed_icon(self, feed_id: int) -> dict:
        """
        Retrieves a feed icon.

        Args:
            feed_id (int): The feed ID.
        Returns:
            A dictionary representing the feed icon.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/feeds/{feed_id}/icon")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_icon(self, icon_id: int) -> dict:
        """
        Retrieves a feed icon.

        Args:
            icon_id (int): The icon ID.
        Returns:
            A dictionary representing the feed icon.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/icons/{icon_id}")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_icon_by_feed_id(self, feed_id: int) -> dict:
        """
        Retrieves a feed icon.

        Args:
            feed_id (int): The feed ID.
        Returns:
            A dictionary representing the feed icon.
        Raises:
            ClientError: If the request fails.
        """
        return self.get_feed_icon(feed_id)

    def create_feed(self, feed_url: str, category_id: Optional[int] = None, **kwargs) -> int:
        """
        Create a new feed.

        Args:
            feed_url (str): The feed URL.
            category_id (int): The category ID.
        Returns:
            int: The feed ID.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/feeds")
        data = dict(feed_url=feed_url, category_id=category_id)
        data.update(kwargs)

        response = self._session.post(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code == 201:
            return response.json()["feed_id"]
        self._handle_error_response(response)

    def update_feed(self, feed_id: int, **kwargs) -> dict:
        """
        Update a feed.

        Args:
            feed_id (int): The feed ID.
        Returns:
            A dictionary representing the updated feed.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/feeds/{feed_id}")
        data = self._get_modification_params(**kwargs)
        response = self._session.put(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code == 201:
            return response.json()
        self._handle_error_response(response)

    def refresh_all_feeds(self) -> bool:
        """
        Refresh all feeds.

        Returns:
            bool: True if the operation was successfully scheduled, False otherwise.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/feeds/refresh")
        response = self._session.put(endpoint, timeout=self._timeout)
        if response.status_code >= 400:
            self._handle_error_response(response)
        return True

    def refresh_feed(self, feed_id: int) -> bool:
        """
        Refreshes a single feed.

        Args:
            feed_id (int): The feed ID.
        Returns:
            bool: True if the operation was successfully scheduled, False otherwise.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/feeds/{feed_id}/refresh")
        response = self._session.put(endpoint, timeout=self._timeout)
        if response.status_code >= 400:
            self._handle_error_response(response)
        return True

    def refresh_category(self, category_id: int) -> bool:
        """
        Refreshes all feeds that belongs to the given category.

        Args:
            category_id (int): The category ID.
        Returns:
            bool: True if the operation was successfully scheduled, False otherwise.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/categories/{category_id}/refresh")
        response = self._session.put(endpoint, timeout=self._timeout)
        if response.status_code >= 400:
            self._handle_error_response(response)
        return True

    def delete_feed(self, feed_id: int) -> None:
        """
        Delete a feed.

        Args:
            feed_id (int): The feed ID.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/feeds/{feed_id}")
        response = self._session.delete(endpoint, timeout=self._timeout)
        if response.status_code != 204:
            self._handle_error_response(response)

    def get_feed_entry(self, feed_id: int, entry_id: int) -> dict:
        """
        Fetch a single entry for a given feed.

        Args:
            feed_id (int): The feed ID.
            entry_id (int): The entry ID.
        Returns:
            A dictionary representing the entry.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/feeds/{feed_id}/entries/{entry_id}")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_feed_entries(self, feed_id: int, **kwargs) -> dict:
        """
        Fetch all entries that belongs to the given feed.

        Args:
            feed_id (int): The feed ID.
        Returns:
            A list of dictionaries representing the entries.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/feeds/{feed_id}/entries")
        params = self._get_params(**kwargs)
        response = self._session.get(
            endpoint,
            params=params,
            timeout=self._timeout,
        )
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def import_entry(
        self,
        feed_id: int,
        url: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        content: Optional[str] = None,
        published_at: Optional[int] = None,
        status: Optional[str] = None,
        starred: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        external_id: Optional[str] = None,
        comments_url: Optional[str] = None,
    ) -> dict:
        """
        Import an entry into the given feed.

        Args:
            feed_id (int): The feed ID.
            url (str): The entry URL (required by the API).
            title (str): The entry title.
            author (str): The entry author.
            content (str): The entry content.
            published_at (int): The publication date as a Unix timestamp.
            status (str): The entry status (read, unread or removed).
            starred (bool): Whether the entry is starred.
            tags (list[str]): Optional list of tags.
            external_id (str): Optional external identifier.
            comments_url (str): Optional comments URL.
        Returns:
            dict: The created entry identifier or existing entry identifier.
        Raises:
            ValueError: If the URL is empty.
            ClientError: If the request fails.
        """
        if not url:
            raise ValueError("url is required")

        endpoint = self._get_endpoint(f"/feeds/{feed_id}/entries/import")
        data = self._get_modification_params(
            **{
                "url": url,
                "title": title,
                "author": author,
                "content": content,
                "published_at": published_at,
                "status": status,
                "starred": starred,
                "tags": tags,
                "external_id": external_id,
                "comments_url": comments_url,
            }
        )

        response = self._session.post(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code in (200, 201):
            return response.json()
        self._handle_error_response(response)

    def mark_feed_entries_as_read(self, feed_id: int) -> None:
        """
        Mark all entries as read in the given feed.

        Args:
            feed_id (int): The feed ID.
        Returns:
            A list of dictionaries representing the entries.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/feeds/{feed_id}/mark-all-as-read")
        response = self._session.put(endpoint, timeout=self._timeout)
        if response.status_code != 204:
            self._handle_error_response(response)

    def get_entry(self, entry_id: int) -> dict:
        """
        Fetch a single entry.

        Args:
            entry_id (int): The entry ID.
        Returns:
            A dictionary representing the entry.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/entries/{entry_id}")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_entries(self, **kwargs) -> dict:
        """
        Fetch all entries.

        Returns:
            A list of dictionaries representing the entries.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/entries")
        params = self._get_params(**kwargs)
        response = self._session.get(
            endpoint,
            params=params,
            timeout=self._timeout,
        )
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def update_entry(self, entry_id: int, title: Optional[str] = None, content: Optional[str] = None) -> dict:
        """
        Update an entry.

        Args:
            entry_id (int): The entry ID.
            title (str): The entry title.
            content (str): The entry content.
        Returns:
            A dictionary representing the updated entry.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/entries/{entry_id}")
        data = self._get_modification_params(
            **{
                "title": title,
                "content": content,
            }
        )
        response = self._session.put(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code == 201:
            return response.json()
        self._handle_error_response(response)

    def update_entries(self, entry_ids: List[int], status: str) -> bool:
        """
        Change the status of multiple entries.

        Args:
            entry_ids (list[int]): The entry IDs.
            status (str): The new status.
        Returns:
            bool: True if the operation was successful, False otherwise.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/entries")
        data = {"entry_ids": entry_ids, "status": status}
        response = self._session.put(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code >= 400:
            self._handle_error_response(response)
        return True

    def fetch_entry_content(self, entry_id: int) -> dict:
        """
        Scrape the entry original URL and returns the content.

        Args:
            entry_id (int): The entry ID.
        Returns:
            A dictionary representing the entry content.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/entries/{entry_id}/fetch-content")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def toggle_bookmark(self, entry_id: int) -> bool:
        """
        Star or unstar an entry.

        Args:
            entry_id (int): The entry ID.
        Returns:
            bool: True if the operation was successful, False otherwise.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/entries/{entry_id}/bookmark")
        response = self._session.put(endpoint, timeout=self._timeout)
        if response.status_code >= 400:
            self._handle_error_response(response)
        return True

    def save_entry(self, entry_id: int) -> bool:
        """
        Send an entry to a third-party service if enabled.

        Args:
            entry_id (int): The entry ID.
        Returns:
            bool: True if the operation was successfully queued, False otherwise.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/entries/{entry_id}/save")
        response = self._session.post(endpoint, timeout=self._timeout)
        if response.status_code != 202:
            self._handle_error_response(response)
        return True

    def get_enclosure(self, enclosure_id: int) -> dict:
        """
        Fetch an enclosure.

        Args:
            enclosure_id (int): The enclosure ID.
        Returns:
            A dictionary representing the enclosure.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/enclosures/{enclosure_id}")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def update_enclosure(self, enclosure_id: int, media_progression: Optional[int] = None) -> bool:
        """
        Update an enclosure.

        Args:
            enclosure_id (int): The enclosure ID.
            media_progression (int): The progression of the media.
        Returns:
            bool: True if the operation was successful, False otherwise.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/enclosures/{enclosure_id}")
        data = self._get_modification_params(media_progression=media_progression)
        response = self._session.put(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code != 204:
            self._handle_error_response(response)
        return True

    def get_categories(self) -> List[dict]:
        """
        Fetch all categories.

        Returns:
            A list of dictionaries representing the categories.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/categories")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_category_entry(self, category_id: int, entry_id: int) -> dict:
        """
        Fetch a single entry for a given category.

        Args:
            category_id (int): The category ID.
            entry_id (int): The entry ID.
        Returns:
            A dictionary representing the entry.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/categories/{category_id}/entries/{entry_id}")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_category_entries(self, category_id: int, **kwargs) -> dict:
        """
        Fetch all entries for a given category.

        Args:
            category_id (int): The category ID.
        Returns:
            A list of dictionaries representing the entries.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/categories/{category_id}/entries")
        params = self._get_params(**kwargs)
        response = self._session.get(
            endpoint,
            params=params,
            timeout=self._timeout,
        )
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def create_category(self, title: str) -> dict:
        """
        Create a new category.

        Args:
            title (str): The category title.
        Returns:
            A dictionary representing the created category.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/categories")
        data = {"title": title}
        response = self._session.post(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code == 201:
            return response.json()
        self._handle_error_response(response)

    def update_category(self, category_id: int, title: str) -> dict:
        """
        Update a category.

        Args:
            category_id (int): The category ID.
            title (str): The category title.
        Returns:
            A dictionary representing the updated category.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/categories/{category_id}")
        data = {"id": category_id, "title": title}
        response = self._session.put(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code == 201:
            return response.json()
        self._handle_error_response(response)

    def delete_category(self, category_id: int) -> None:
        """
        Delete a category.

        Args:
            category_id (int): The category ID.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/categories/{category_id}")
        response = self._session.delete(endpoint, timeout=self._timeout)
        if response.status_code != 204:
            self._handle_error_response(response)

    def mark_category_entries_as_read(self, category_id: int) -> None:
        """
        Mark all entries as read in the given category.

        Args:
            category_id (int): The category ID.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/categories/{category_id}/mark-all-as-read")
        response = self._session.put(endpoint, timeout=self._timeout)
        if response.status_code != 204:
            self._handle_error_response(response)

    def get_users(self) -> List[dict]:
        """
        Fetch all users.

        Returns:
            A list of dictionaries representing users.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/users")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_user_by_id(self, user_id: int) -> dict:
        """
        Fetch a user by its ID.

        Args:
            user_id (int): The user ID.
        Returns:
            A dictionary representing the user.
        Raises:
            ClientError: If the request fails.
        """
        return self._get_user(user_id)

    def get_user_by_username(self, username: str) -> dict:
        """
        Fetch a user by its username.

        Args:
            username (str): The username.
        Returns:
            A dictionary representing the user.
        Raises:
            ClientError: If the request fails.
        """
        return self._get_user(username)

    def _get_user(self, user_id_or_username: Union[str, int]) -> dict:
        endpoint = self._get_endpoint(f"/users/{user_id_or_username}")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def create_user(self, username: str, password: str, is_admin: bool = False) -> dict:
        """
        Create a new user.

        Args:
            username (str): The username.
            password (str): The password.
            is_admin (bool): Whether the user should be an administrator.
        Returns:
            A dictionary representing the created user.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/users")
        data = {"username": username, "password": password, "is_admin": is_admin}
        response = self._session.post(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code == 201:
            return response.json()
        self._handle_error_response(response)

    def update_user(self, user_id: int, **kwargs) -> dict:
        """
        Update a user.

        Args:
            user_id (int): The user ID.
        Returns:
            A dictionary representing the updated user.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/users/{user_id}")
        data = self._get_modification_params(**kwargs)
        response = self._session.put(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code == 201:
            return response.json()
        self._handle_error_response(response)

    def delete_user(self, user_id: int) -> None:
        """
        Remove a user.

        Args:
            user_id (int): The user ID.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/users/{user_id}")
        response = self._session.delete(endpoint, timeout=self._timeout)
        if response.status_code != 204:
            self._handle_error_response(response)

    def mark_user_entries_as_read(self, user_id: int) -> None:
        """
        Mark all entries as read for a given user.

        Args:
            user_id (int): The user ID.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/users/{user_id}/mark-all-as-read")
        response = self._session.put(endpoint, timeout=self._timeout)
        if response.status_code != 204:
            self._handle_error_response(response)

    def get_feed_counters(self) -> dict:
        """
        Get the number of read and unread entries per feed.

        Returns:
            A dictionary containing the number of read and unread entries per feed.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/feeds/counters")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def get_integrations_status(self) -> bool:
        """
        Get the status of third-party integrations.

        Returns:
            bool: True if at least one third-party integration is enabled, False otherwise.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/integrations/status")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()["has_integrations"]
        self._handle_error_response(response)

    def get_api_keys(self) -> List[dict]:
        """
        Get all API keys for the current user.

        Returns:
            List[dict]: A list of API keys.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/api-keys")
        response = self._session.get(endpoint, timeout=self._timeout)
        if response.status_code == 200:
            return response.json()
        self._handle_error_response(response)

    def create_api_key(self, description: str) -> dict:
        """
        Create a new API key.

        Args:
            description (str): The description for the API key.
        Returns:
            dict: The created API key.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint("/api-keys")
        data = {"description": description}
        response = self._session.post(
            endpoint,
            data=json.dumps(data),
            timeout=self._timeout,
        )
        if response.status_code == 201:
            return response.json()
        self._handle_error_response(response)

    def delete_api_key(self, api_key_id: int) -> None:
        """
        Delete an API key.

        Args:
            api_key_id (int): The ID of the API key to delete.
        Raises:
            ClientError: If the request fails.
        """
        endpoint = self._get_endpoint(f"/api-keys/{api_key_id}")
        response = self._session.delete(endpoint, timeout=self._timeout)
        if response.status_code != 204:
            self._handle_error_response(response)

    def close(self) -> None:
        """
        Close the underlying session
        """
        self._session.close()
