# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rtv.content import SubscriptionContent
from rtv.oauth import OAuthHelper

import vcr
import praw

try:
    from unittest import mock
except ImportError:
    import mock


def test_content_helpers(terminal, config):

    with vcr.use_cassette('fixtures/cassettes/rtv.yaml', record_mode='all'):
        config.load_refresh_token()

        reddit = praw.Reddit(
            user_agent='rtv test suite',
            decode_html_entities=False)
        reddit.set_oauth_app_info(
            config['oauth_client_id'],
            config['oauth_client_secret'],
            config['oauth_redirect_uri'])
        reddit.refresh_access_information(config.refresh_token)

# def test_humanize_timestamp():
#
#     timestamp = time.time() - 30
#     assert humanize_timestamp(timestamp) == '0min'
#     assert humanize_timestamp(timestamp, verbose=True) == 'moments ago'
#
#     timestamp = time.time() - 60 * 60 * 24 * 30.4 * 12
#     assert humanize_timestamp(timestamp) == '11month'
#     assert humanize_timestamp(timestamp, verbose=True) == '11 months ago'
#
#     timestamp = time.time() - 60 * 60 * 24 * 30.4 * 12 * 5
#     assert humanize_timestamp(timestamp) == '5yr'
#     assert humanize_timestamp(timestamp, verbose=True) == '5 years ago'