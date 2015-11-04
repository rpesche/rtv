# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import requests
from tornado import gen, ioloop
from concurrent.futures import ThreadPoolExecutor

try:
    from unittest import mock
except ImportError:
    import mock


def test_set_mobile_url(oauth):

    if oauth.term.display:
        assert '.compact' not in oauth.reddit.config.API_PATHS['authorize']
    else:
        assert '.compact' in oauth.reddit.config.API_PATHS['authorize']


def test_authorize(oauth, config):

    @gen.coroutine
    def authorize_request():
        with ThreadPoolExecutor(max_workers=1) as executor:
            yield executor.submit(requests.get, config['oauth_redirect_uri'])

    ioloop.IOLoop.current().add_callback(authorize_request)
    oauth.authorize()
    pass