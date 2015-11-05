# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time

import tornado
import requests

from rtv.oauth import OAuthHelper

try:
    from unittest import mock
except ImportError:
    import mock


def close_iloop(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        finally:
            tornado.ioloop.IOLoop.current().close(all_fds=True)
    return wrapper


def test_terminal_non_mobile_authorize(reddit, terminal, config):

    # Should direct to the desktop version if using a graphical browser
    terminal._display = True
    oauth = OAuthHelper(reddit, terminal, config)
    assert '.compact' not in oauth.reddit.config.API_PATHS['authorize']


def test_terminal_mobile_authorize(reddit, terminal, config):

    # Should direct to the mobile version if using a terminal browser
    terminal._display = False
    oauth = OAuthHelper(reddit, terminal, config)
    assert '.compact' in oauth.reddit.config.API_PATHS['authorize']


def test_authorize_with_refresh_token(oauth):

    # If there is already a refresh token skip the OAuth process
    oauth.config.refresh_token = 'secrettoken'
    oauth.authorize()
    assert oauth.reddit.refresh_access_information.called
    assert oauth.http_server is None

@close_iloop
def test_authorize_background_browser(oauth, reddit, stdscr):

    params = {'state': 'uniqueid', 'code': 'secretcode', 'error': None}
    oauth.term._display = False

    def click_authorize(*args, **kwargs):
        """
        After the browser opens, wait a short duration and mock authorizing the
        application by sending a new request to the redirect url
        """
        time.sleep(0.5)
        requests.get(oauth.config['oauth_redirect_uri'], params)

    # Because we use `from .helpers import open_browser` we have to patch the
    # function in the destination oauth module and not the helpers module
    with mock.patch('uuid.UUID.hex', new_callable=mock.PropertyMock) as uuid, \
            mock.patch('rtv.oauth.open_browser') as open_browser, \
            mock.patch.object(reddit, 'user'):

        uuid.return_value = params['state']
        open_browser.side_effect = click_authorize

        oauth.authorize()
        stdscr.subwin.addstr.assert_called_with(1, 1, 'Redirecting to reddit')
        assert open_browser.called
        reddit.get_access_information.assert_called_with(params['code'])
        assert oauth.config.refresh_token is not None
        assert oauth.config.save_refresh_token.called