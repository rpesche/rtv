# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rtv.subreddit import SubredditPage

try:
    from unittest import mock
except ImportError:
    import mock


def test_subreddit_page_draw(reddit, terminal, config, oauth):

    window = terminal.stdscr.subwin

    with terminal.loader():
        page = SubredditPage(reddit, terminal, config, oauth, '/r/python')
    assert terminal.loader.exception is None

    page.draw()

    # Title
    title = '/r/python'.encode('utf-8')
    window.addstr.assert_any_call(0, 0, title)

    # Submission
    text = page.content.get(0)['split_title'][0].encode('utf-8')
    window.subwin.addstr.assert_any_call(0, 1, text, 2097152)

    # Cursor should have been drawn
    assert window.subwin.chgat.called

    # Reload with a smaller terminal window
    terminal.stdscr.ncols = 20
    terminal.stdscr.nlines = 10
    with terminal.loader():
        page = SubredditPage(reddit, terminal, config, oauth, '/r/python')
    assert terminal.loader.exception is None

    page.draw()


def test_subreddit_page(reddit, terminal, config, oauth, refresh_token):

    with terminal.loader():
        page = SubredditPage(reddit, terminal, config, oauth, name='/r/python')
    assert terminal.loader.exception is None

    page.draw()

    # refresh content with name and order
    # search subreddit
    # prompt subreddit
    # open submission
    # open link
    # post submission
    # open subscriptions
    # git treat cassettes as binary!

