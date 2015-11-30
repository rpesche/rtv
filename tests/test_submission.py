# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import curses

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
    text = comment_data['split_body'][0].encode('utf-8')
    window.subwin.addstr.assert_any_call(1, 1, text)

    # More Comments
    comment_data = page.content.get(1)
    text = comment_data['body'].encode('utf-8')
    window.subwin.addstr.assert_any_call(0, 1, text)

    # Cursor should not be drawn when the page is first opened
    assert not window.subwin.chgat.called

    # Reload with a smaller terminal window
    terminal.stdscr.ncols = 20
    terminal.stdscr.nlines = 10
    with terminal.loader():
        page = SubmissionPage(reddit, terminal, config, oauth, url=url)
    assert terminal.loader.exception is None

    page.draw()


def test_submission_page(reddit, terminal, config, oauth, refresh_token):

    url = ('https://www.reddit.com/r/Python/comments/2xmo63/'
           'a_python_terminal_viewer_for_browsing_reddit')

    with terminal.loader():
        page = SubmissionPage(reddit, terminal, config, oauth, url=url)
    assert terminal.loader.exception is None

    page.draw()

    # Should be able to refresh content
    page.refresh_content()

    # Unauthenticated commands
    methods = [
        'a',  # Upvote
        'z',  # Downvote
        'c',  # Comment
        'e',  # Edit
        'd',  # Delete
    ]
    for ch in methods:
        page.controller.trigger(ch)
        text = 'Not logged in'.encode('utf-8')
        terminal.stdscr.subwin.addstr.assert_called_with(1, 1, text)

    # Open the selected link
    with mock.patch.object(terminal, 'open_browser'):
        page.controller.trigger(terminal.RETURN)
        assert terminal.open_browser.called

    # Log in
    config.refresh_token = refresh_token
    oauth.authorize()

    # Test voting on the submission
    with mock.patch('praw.objects.Submission.upvote') as upvote,            \
            mock.patch('praw.objects.Submission.downvote') as downvote,     \
            mock.patch('praw.objects.Submission.clear_vote') as clear_vote:

        # Upvote
        page.controller.trigger('a')
        assert upvote.called
        assert page.content.get(page.nav.absolute_index)['likes'] is True

        # Downvote
        page.controller.trigger('z')
        assert downvote.called
        assert page.content.get(page.nav.absolute_index)['likes'] is False

        # Clear vote
        page.controller.trigger('z')
        assert clear_vote.called
        assert page.content.get(page.nav.absolute_index)['likes'] is None

        # Upvote - exception
        upvote.side_effect = KeyboardInterrupt()
        page.controller.trigger('a')
        assert page.content.get(page.nav.absolute_index)['likes'] is None

        # Downvote - exception
        downvote.side_effect = KeyboardInterrupt()
        page.controller.trigger('a')
        assert page.content.get(page.nav.absolute_index)['likes'] is None

    # Leave a comment
    with mock.patch('praw.objects.Submission.add_comment') as add_comment, \
            mock.patch.object(terminal, 'open_editor') as open_editor,     \
            mock.patch('time.sleep'):
        open_editor.return_value = 'comment text'

        page.controller.trigger('c')
        assert open_editor.called
        add_comment.assert_called_with('comment text')

    # Can't delete the submission
    curses.flash.reset_mock()
    page.controller.trigger('d')
    assert curses.flash.called

    # Move down to the first comment
    page.controller.trigger('j')

    # Try to delete the first comment - wrong author
    curses.flash.reset_mock()
    page.controller.trigger('d')
    assert curses.flash.called

    # Spoof the author and try to delete again
    page.content.get(page.nav.absolute_index)['author'] = reddit.user.name
    with mock.patch('praw.objects.Comment.delete') as delete,     \
            mock.patch.object(terminal.stdscr, 'getch') as getch, \
            mock.patch('time.sleep'):
        getch.return_value = ord('y')

        page.controller.trigger('d')
        assert delete.called

    # Try to edit the submission - wrong author
    curses.flash.reset_mock()
    page.controller.trigger('e')
    assert curses.flash.called

    # Spoof the submission and try to edit again
    page.content.get(page.nav.absolute_index)['author'] = reddit.user.name
    with mock.patch('praw.objects.Submission.edit') as edit,           \
            mock.patch.object(terminal, 'open_editor') as open_editor, \
            mock.patch('time.sleep'):
        open_editor.return_value = 'submission text'

        page.controller.trigger('e')
        assert open_editor.called
        edit.assert_called_with('submission text')

    # Move down to the first comment
    page.controller.trigger('j')

    # Spoof the author and edit the comment
    page.content.get(page.nav.absolute_index)['author'] = reddit.user.name
    with mock.patch('praw.objects.Comment.edit') as edit,              \
            mock.patch.object(terminal, 'open_editor') as open_editor, \
            mock.patch('time.sleep'):
        open_editor.return_value = 'comment text'

        page.controller.trigger('e')
        assert open_editor.called
        edit.assert_called_with('comment text')