# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time

from rtv.helpers import (open_editor, open_browser, wrap_text,
                         strip_subreddit_url, humanize_timestamp)

try:
    from unittest import mock
except ImportError:
    import mock


def test_humanize_timestamp():

    timestamp = time.time() - 30
    assert humanize_timestamp(timestamp) == '0min'
    assert humanize_timestamp(timestamp, verbose=True) == 'moments ago'

    timestamp = time.time() - 60 * 60 * 24 * 30.4 * 12
    assert humanize_timestamp(timestamp) == '11month'
    assert humanize_timestamp(timestamp, verbose=True) == '11 months ago'

    timestamp = time.time() - 60 * 60 * 24 * 30.4 * 12 * 5
    assert humanize_timestamp(timestamp) == '5yr'
    assert humanize_timestamp(timestamp, verbose=True) == '5 years ago'
