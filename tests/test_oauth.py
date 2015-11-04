# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from unittest import mock
except ImportError:
    import mock


def test_set_mobile_url(oauth):

    if oauth.term.display:
        assert '.compact' not in oauth.reddit.config.API_PATHS['authorize']
    else:
        assert '.compact' in oauth.reddit.config.API_PATHS['authorize']


def test_authorize(oauth):

    oauth.authorize()
    pass