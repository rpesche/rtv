# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rtv.subreddit import SubredditPage
from rtv.content import SubmissionContent

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

    # Refresh the page with default values
    page.controller.trigger('r')
    assert page.content.order is None
    assert page.content.name == '/r/python'
    assert terminal.loader.exception is None

    # Refresh with the order in the name
    page.refresh_content(name='/r/python/hot', order='ignore')
    assert page.content.order == 'hot'
    assert page.content.name == '/r/python'
    assert terminal.loader.exception is None

    # Search the current subreddit
    with mock.patch.object(terminal, 'prompt_input'):
        terminal.prompt_input.return_value = 'search term'
        page.controller.trigger('f')
        assert page.content.name == '/r/python'
        assert terminal.prompt_input.called
        assert not terminal.loader.exception

    # Searching with an empty query shouldn't crash
    with mock.patch.object(terminal, 'prompt_input'):
        terminal.prompt_input.return_value = None
        page.controller.trigger('f')
        assert not terminal.loader.exception

    # Prompt for a different subreddit
    with mock.patch.object(terminal, 'prompt_input'):
        terminal.prompt_input.return_value = 'front/top'
        page.controller.trigger('/')
        assert page.content.name == '/r/front'
        assert page.content.order == 'top'
        assert not terminal.loader.exception

    # Open the selected submission
    data = page.content.get(page.nav.absolute_index)
    with mock.patch('rtv.submission.SubmissionPage.loop') as loop, \
            mock.patch.object(config.history, 'add'):
        data['url_type'] = 'selfpost'
        page.controller.trigger('l')
        assert not terminal.loader.exception
        assert loop.called
        config.history.add.assert_called_with(data['url_full'])

    # Open the selected link externally
    with mock.patch.object(terminal, 'open_browser'), \
            mock.patch.object(config.history, 'add'):
        data['url_type'] = 'external'
        page.controller.trigger('o')
        assert terminal.open_browser.called
        config.history.add.assert_called_with(data['url_full'])

    # Open the selected link within rtv
    with mock.patch.object(page, 'open_submission'), \
            mock.patch.object(config.history, 'add'):
        data['url_type'] = 'selfpost'
        page.controller.trigger('o')
        assert page.open_submission.called

    # Unauthenticated commands
    methods = [
        'a',  # Upvote
        'z',  # Downvote
        'c',  # Post
        'e',  # Edit
        'd',  # Delete
        's',  # Subscriptions
    ]
    for ch in methods:
        page.controller.trigger(ch)
        text = 'Not logged in'.encode('utf-8')
        terminal.stdscr.subwin.addstr.assert_called_with(1, 1, text)

    # Log in
    config.refresh_token = refresh_token
    oauth.authorize()

    page.refresh_content('front')

    # Post a submission to an invalid subreddit
    page.controller.trigger('c')
    text = "Can't post to /r/front".encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_called_with(1, 1, text)

    page.refresh_content('python')

    # Post a submission with a title but with no body
    with mock.patch.object(terminal, 'open_editor'):
        terminal.open_editor.return_value = 'title'
        page.controller.trigger('c')
        text = "Aborted".encode('utf-8')
        terminal.stdscr.subwin.addstr.assert_called_with(1, 1, text)

    # Post a fake submission
    url = 'https://www.reddit.com/r/Python/comments/2xmo63/'
    submission = reddit.get_submission(url)
    with mock.patch.object(terminal, 'open_editor'),  \
            mock.patch.object(reddit, 'submit'),      \
            mock.patch('rtv.page.Page.loop') as loop, \
            mock.patch('time.sleep'):
        terminal.open_editor.return_value = 'test\ncontent'
        reddit.submit.return_value = submission
        page.controller.trigger('c')
        assert reddit.submit.called
        assert loop.called

    # Select a subscription
    with mock.patch('rtv.page.Page.loop') as loop:
        page.controller.trigger('s')
        assert loop.called


