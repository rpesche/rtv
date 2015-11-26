# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rtv.submission import SubmissionPage

try:
    from unittest import mock
except ImportError:
    import mock


def test_submission_page_draw(reddit, terminal, config, oauth):

    window = terminal.stdscr.subwin
    url = ('https://www.reddit.com/r/Python/comments/2xmo63/'
           'a_python_terminal_viewer_for_browsing_reddit')

    with terminal.loader():
        page = SubmissionPage(reddit, terminal, config, oauth, url=url)
    assert terminal.loader.exception is None

    # Toggle the second comment so we can check the draw more comments method
    page.content.toggle(1)
    page.draw()

    #  Title
    title = url[:terminal.stdscr.ncols-1].encode('utf-8')
    window.addstr.assert_any_call(0, 0, title)

    # Submission
    submission_data = page.content.get(-1)
    text = submission_data['title'].encode('utf-8')
    window.subwin.addstr.assert_any_call(1, 1, text, 2097152)
    assert window.subwin.border.called

    # Comment
    comment_data = page.content.get(0)
    for i, line in enumerate(comment_data['split_body'], start=1):
        if line:
            text = line.encode('utf-8')
            window.subwin.addstr.assert_any_call(i, 1, text)

    # Cursor should not be called when the page is first opened
    assert not window.subwin.chgat.called

    # Reload with a smaller terminal window
    terminal.stdscr.ncols = 20
    terminal.stdscr.nlines = 10
    with terminal.loader():
        page = SubmissionPage(reddit, terminal, config, oauth, url=url)
    assert terminal.loader.exception is None

    page.draw()

# TODO: Test post, edit, delete