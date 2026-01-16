Miniflux Python API Client
==========================

Python client library for [Miniflux](https://miniflux.app).

Requirements
------------

- Miniflux >= 2.0.49
- Python >= 3.8
- requests

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

Installation
------------

```bash
python3 -m pip install miniflux
```

Running Tests
-------------

```bash
python3 -m unittest -v
```

Examples
--------

```python
import miniflux

# Creating a client using username / password authentication
client = miniflux.Client("https://miniflux.example.org", username="my_username", password="my_secret_password")

# Use an API Key (preferred method)
client = miniflux.Client("https://miniflux.example.org", api_key="My secret API token")

# Get all feeds
feeds = client.get_feeds()

# Refresh a feed
client.refresh_feed(123)

# Discover subscriptions from a website
subscriptions = client.discover("https://example.org")

# Create a new feed, with a personalized user agent and with the crawler enabled
feed_id = client.create_feed("http://example.org/feed.xml", category_id=42, crawler=True, user_agent="GoogleBot")

# Fetch 10 starred entries
entries = client.get_entries(starred=True, limit=10)

# Fetch last 5 feed entries
feed_entries = client.get_feed_entries(123, direction='desc', order='published_at', limit=5)

# Fetch entries that belongs to a category with status unread and read
entries = client.get_entries(category_id=456, status=['read', 'unread'])

# Update entry title and content
client.update_entry(entry_id=1234, title="New title", content="New content")

# Import an entry with a Unix timestamp
client.import_entry(feed_id=123, url="https://example.org/article", published_at=1736200000)

# Update a feed category
client.update_feed(123, category_id=456)

# OPML Export
opml = client.export_feeds()

# OPML import
client.import_feeds(opml_data)

# Get application version
client.get_version()

# Flush history
client.flush_history()

# Get current user
myself = client.me()
```

You can also use a context manager:

```python
import miniflux

with miniflux.Client("https://miniflux.domain.tld", api_key="secret") as clt:
    clt.me()
```

Available Methods
-----------------

The following methods are available on the `miniflux.Client` object:

#### Application

- `get_version()`
- `get_integrations_status()`

#### Subscriptions

- `export_feeds()`
- `import_feeds(opml: str)`
- `discover(website_url: str, **kwargs)`

#### Category Management

- `get_categories()`
- `get_category_entry(category_id: int, entry_id: int)`
- `get_category_entries(category_id: int, **kwargs)`
- `create_category(title: str)`
- `update_category(category_id: int, title: str)`
- `delete_category(category_id: int)`

#### Feed Management

- `get_category_feeds(category_id: int)`
- `get_feeds()`
- `get_feed(feed_id: int)`
- `get_feed_icon(feed_id: int)`
- `get_icon(icon_id: int)`
- `get_icon_by_feed_id(feed_id: int)`
- `create_feed(feed_url: str, category_id: int|None = None, **kwargs)`
- `update_feed(feed_id: int, **kwargs)`
- `refresh_all_feeds()`
- `refresh_feed(feed_id: int)`
- `refresh_category(category_id: int)`
- `delete_feed(feed_id: int)`
- `get_feed_counters()`

#### Entry Management

- `flush_history()`
- `get_feed_entry(feed_id: int, entry_id: int)`
- `get_feed_entries(feed_id: int, **kwargs)`
- `import_entry(feed_id: int, url: str, **kwargs)`
- `mark_feed_entries_as_read(feed_id: int)`
- `get_entry(entry_id: int)`
- `get_entries(**kwargs)`
- `update_entry(entry_id: int, title: str|None = None, content: str|None = None)`
- `update_entries(entry_ids: list[int], status: str)`
- `fetch_entry_content(entry_id: int)`
- `toggle_bookmark(entry_id: int)`
- `save_entry(entry_id: int)`
- `get_enclosure(enclosure_id: int)`
- `update_enclosure(enclosure_id: int, media_progression: Optional[int] = None)`
- `mark_category_entries_as_read(category_id: int)`
- `mark_user_entries_as_read(user_id: int)`

#### User Management

- `me()`
- `get_users()`
- `get_user_by_id(user_id: int)`
- `get_user_by_username(username: str)`
- `create_user(username: str, password: str, is_admin: bool = False)`
- `update_user(user_id: int, **kwargs)`
- `delete_user(user_id: int)`

#### API Keys

- `get_api_keys()`
- `create_api_key(description: str)`
- `delete_api_key(api_key_id: int)`

Look at [miniflux.py](https://github.com/miniflux/python-client/blob/main/miniflux.py) for the complete list of methods and their detailed parameters.

Author
------

Frédéric Guillot

License
-------

This library is distributed under MIT License.
