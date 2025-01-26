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

Look at [miniflux.py](https://github.com/miniflux/python-client/blob/main/miniflux.py) for the complete list of methods.

Author
------

Frédéric Guillot

License
-------

This library is distributed under MIT License.
