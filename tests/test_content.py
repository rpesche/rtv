# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six
import praw
import time
from vcr import VCR

from rtv.oauth import OAuthHelper
from rtv.content import (Content, SubmissionContent, SubscriptionContent,
                         SubredditContent)

try:
    from unittest import mock
except ImportError:
    import mock


def test_humanize_timestamp():

    timestamp = time.time() - 30
    assert Content.humanize_timestamp(timestamp) == '0min'
    assert Content.humanize_timestamp(timestamp, True) == 'moments ago'

    timestamp = time.time() - 60 * 60 * 24 * 30.4 * 12
    assert Content.humanize_timestamp(timestamp) == '11month'
    assert Content.humanize_timestamp(timestamp, True) == '11 months ago'

    timestamp = time.time() - 60 * 60 * 24 * 30.4 * 12 * 5
    assert Content.humanize_timestamp(timestamp) == '5yr'
    assert Content.humanize_timestamp(timestamp, True) == '5 years ago'


def test_wrap_text():

    text = 'four score\nand seven\n\n'
    assert Content.wrap_text(text, 6) == ['four', 'score', 'and', 'seven', '']
    assert Content.wrap_text(text, 15) == ['four score', 'and seven', '']
    assert Content.wrap_text('', 70) == []
    assert Content.wrap_text('\n\n\n\n', 70) == ['', '', '', '']


def test_content_submission_post(reddit, terminal):

    submission = next(reddit.get_top())
    content = SubmissionContent(submission, terminal.loader)

    # Everything should be converted to unicode by this point
    for data in content.iterate(-1, 1):
        for val in data.values():
            assert not isinstance(val, six.binary_type)
        break