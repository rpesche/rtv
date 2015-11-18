# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time

import praw
import pytest

from rtv.content import *

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


def test_content_submission_initialize(reddit, terminal):

    url = 'https://www.reddit.com/r/Python/comments/2xmo63/'
    submission = reddit.get_submission(url)
    content = SubmissionContent(submission, terminal.loader, indent_size=3,
                                max_indent_level=4, order='top')
    assert content.indent_size == 3
    assert content.max_indent_level == 4
    assert content.order == 'top'
    assert content.name is not None


def test_content_submission(reddit, terminal):

    url = 'https://www.reddit.com/r/Python/comments/2xmo63/'
    submission = reddit.get_submission(url)
    content = SubmissionContent(submission, terminal.loader)

    # Everything is loaded upon instantiation
    assert len(content._comment_data) == 45
    assert content.get(-1)['type'] == 'Submission'
    assert content.get(40)['type'] == 'Comment'

    for data in content.iterate(-1, 1):
        assert all(k in data for k in ('object', 'n_rows', 'offset', 'type'))
        # All text should be converted to unicode by this point
        for val in data.values():
            assert not isinstance(val, six.binary_type)

    # Out of bounds
    with pytest.raises(IndexError):
        content.get(-2)
    with pytest.raises(IndexError):
        content.get(50)

    # Toggling the submission doesn't do anything
    content.toggle(-1)
    assert len(content._comment_data) == 45

    # Toggling a comment hides its 3 children
    content.toggle(2)
    data = content.get(2)
    assert data['type'] == 'HiddenComment'
    assert data['count'] == 3
    assert data['level'] >= content.get(3)['level']
    assert len(content._comment_data) == 43

    # Toggling again expands the children
    content.toggle(2)
    assert len(content._comment_data) == 45


def test_content_submission_load_more_comments(reddit, terminal):

    url = 'https://www.reddit.com/r/AskReddit/comments/2np694/'
    submission = reddit.get_submission(url)
    content = SubmissionContent(submission, terminal.loader)
    assert len(content._comment_data) == 391

    # More comments load when toggled
    assert content.get(390)['type'] == 'MoreComments'
    content.toggle(390)
    assert len(content._comment_data) > 390
    assert content.get(390)['type'] == 'Comment'


def test_content_submission_from_url(reddit, terminal):

    url = 'https://www.reddit.com/r/AskReddit/comments/2np694/'
    SubmissionContent.from_url(reddit, url, terminal.loader)
    SubmissionContent.from_url(reddit, url, terminal.loader, order='new')

    # Invalid sorting order doesn't raise an exception
    SubmissionContent.from_url(reddit, url, terminal.loader, order='fake')
    assert not terminal.loader.exception

    # Invalid comment URL
    content = SubmissionContent.from_url(reddit, url[:-2], terminal.loader)
    assert content is None
    assert isinstance(terminal.loader.exception, praw.errors.NotFound)
    message = 'Not Found'.encode('utf-8')
    terminal.stdscr.derwin().addstr.assert_called_with(1, 1, message)


def test_content_subreddit_initialize(reddit, terminal):

    submissions = reddit.get_subreddit('python').get_top(limit=None)
    content = SubredditContent('python', submissions, terminal.loader, 'top')
    assert content.name == 'python'
    assert content.order == 'top'
    assert len(content._submission_data) == 1


def test_content_subreddit_initialize_invalid(reddit, terminal):

    submissions = reddit.get_subreddit('invalidsubreddit7').get_top(limit=None)
    content = SubredditContent('python', submissions, terminal.loader, 'top')
    assert len(content._submission_data) == 0
    assert isinstance(terminal.loader.exception, praw.errors.InvalidSubreddit)
    message = 'Invalid Subreddit'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_called_with(1, 1, message)