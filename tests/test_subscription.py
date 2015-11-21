# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import praw
import curses

from rtv.subscription import SubscriptionPage

try:
    from unittest import mock
except ImportError:
    import mock


def test_subscription_page(reddit, terminal, config, oauth, refresh_token):

    # Can't load page if not logged in
    with terminal.loader():
        SubscriptionPage(reddit, terminal, config, oauth)
    assert isinstance(
        terminal.loader.exception, praw.errors.LoginOrScopeRequired)

    config.refresh_token = refresh_token
    oauth.authorize()

    # Instantiate when logged in
    with terminal.loader():
        page = SubscriptionPage(reddit, terminal, config, oauth)
    assert terminal.loader.exception is None

    # Refresh content - invalid order
    page.controller.trigger(curses.KEY_F5, order='hot')
    assert terminal.stdscr.flash.called
    terminal.stdscr.reset_mock()

    # Refresh content
    page.controller.trigger('r')
    assert not terminal.stdscr.flash.called

    # Move cursor down
    page.controller.trigger('j')
    pass