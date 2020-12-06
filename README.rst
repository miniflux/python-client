Miniflux Python API Client
==========================

.. image:: https://badge.fury.io/py/miniflux.svg
    :target: https://badge.fury.io/py/miniflux

Python client library for Miniflux API.

Dependencies
------------

- Miniflux >= 2.x
- Python >= 3.6
- requests

Installation
------------

.. code:: bash

    pip install miniflux

Running Tests
-------------

.. code:: bash

    python setup.py test

Usage Example
-------------

.. code:: python

    import miniflux

    # Creating a client using username / password authentication
    client = miniflux.Client("https://miniflux.example.org", "my_username", "my_secret_password")

    # Use an API Key (preferred method)
    client = miniflux.Client("https://miniflux.example.org", api_key="My secret API token")

    # Get all feeds
    feeds = client.get_feeds()

    # Refresh a feed
    client.refresh_feed(123)

    # Discover subscriptions from a website
    subscriptions = client.discover("https://example.org")

    # Create a new feed, with a personalized user agent and with the crawler enabled
    feed_id = client.create_feed("http://example.org/feed.xml", 42, crawler=True, user_agent="GoogleBot")

    # Fetch 10 starred entries
    entries = client.get_entries(starred=True, limit=10)

    # Fetch last 5 feed entries
    feed_entries = client.get_feed_entries(123, direction='desc', order='published_at', limit=5)

    # Fetch entries that belongs to a category with status unread and read
    entries = client.get_entries(category_id=456, status=['read', 'unread'])

    # Update a feed category
    client.update_feed(123, category_id=456)

    # OPML Export
    opml = client.export_feeds()

    # Get application version
    client.get_version()

Author
------

Frédéric Guillot

License
-------

This library is distributed under MIT License.
