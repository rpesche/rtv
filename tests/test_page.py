# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from rtv.page import Page, Controller, logged_in

try:
    from unittest import mock
except ImportError:
    import mock


def test_logged_in(terminal):

    page = mock.MagicMock()
    page.term = terminal

    @logged_in
    def func(page):
        raise RuntimeError()

    # Logged in runs the function
    page.reddit.is_oauth_session.return_value = True
    with pytest.raises(RuntimeError):
        func(page)
    message = 'Not logged in'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_not_called_with(1, 1, message)

    # Logged out skips the function and displays a message
    page.reddit.is_oauth_session.return_value = False
    func(page)
    message = 'Not logged in'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_called_with(1, 1, message)


def test_page_unauthenticated(reddit, terminal, config, oauth):

    page = Page(reddit, terminal, config, oauth)
    page.content = mock.MagicMock()
    page.nav = mock.MagicMock()
    page.controller = Controller(page)
    page.refresh_content = mock.MagicMock()

    # Quit, confirm
    terminal.stdscr.getch.return_value = ord('y')
    with mock.patch('sys.exit') as sys_exit:
        page.controller.trigger('q')
    assert sys_exit.called

    # Quit, deny
    terminal.stdscr.getch.return_value = terminal.ESCAPE
    with mock.patch('sys.exit') as sys_exit:
        page.controller.trigger('q')
    assert not sys_exit.called

    # Force quit
    terminal.stdscr.getch.return_value = terminal.ESCAPE
    with mock.patch('sys.exit') as sys_exit:
        page.controller.trigger('Q')
    assert sys_exit.called

    # Show help
    page.controller.trigger('?')
    message = 'Basic Commands'.encode('utf-8')
    terminal.stdscr.subwin.addstr.assert_any_call(1, 1, message)

    # Sort content
    page.controller.trigger('1')
    page.refresh_content.assert_called_with(order='hot')
    page.controller.trigger('2')
    page.refresh_content.assert_called_with(order='top')
    page.controller.trigger('3')
    page.refresh_content.assert_called_with(order='rising')
    page.controller.trigger('4')
    page.refresh_content.assert_called_with(order='new')
    page.controller.trigger('5')
    page.refresh_content.assert_called_with(order='controversial')