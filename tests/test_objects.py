# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import curses

import pytest
import requests

from rtv.objects import Color, LoadScreen, curses_session


@pytest.mark.parametrize('ascii', [True, False])
def test_load_screen(terminal, stdscr, ascii):
    terminal.ascii = ascii

    # Ensure the thread is properly started/stopped
    with terminal.loader(delay=0, message=u'Hello', trail=u'...'):
        assert terminal.loader._animator.is_alive()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert terminal.loader.exception is None
    assert stdscr.subwin.ncols == 10
    assert stdscr.subwin.nlines == 3
    stdscr.refresh.assert_called()


@pytest.mark.parametrize('ascii', [True, False])
def test_load_screen_exception_unhandled(terminal, stdscr, ascii):
    terminal.ascii = ascii

    # Raising an exception should clean up the loader properly
    with pytest.raises(Exception):
        with terminal.loader(delay=0):
            assert terminal.loader._animator.is_alive()
            raise Exception()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    stdscr.refresh.assert_called()


@pytest.mark.parametrize('ascii', [True, False])
def test_load_screen_exception_handled(terminal, stdscr, ascii):
    terminal.ascii = ascii

    # Raising a handled exception should get stored on the loaders
    with terminal.loader(delay=0):
        assert terminal.loader._animator.is_alive()
        raise requests.ConnectionError()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert isinstance(terminal.loader.exception, requests.ConnectionError)
    error_message = 'Connection Error'.encode('ascii' if ascii else 'utf-8')
    stdscr.subwin.addstr.assert_called_with(1, 1, error_message)
    stdscr.refresh.assert_called()


@pytest.mark.parametrize('ascii', [True, False])
def test_load_screen_keyboard_interrupt(terminal, stdscr, ascii):
    terminal.ascii = ascii

    # Raising a KeyboardInterrupt should be also be stored
    with terminal.loader(delay=0):
        assert terminal.loader._animator.is_alive()
        raise KeyboardInterrupt()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert isinstance(terminal.loader.exception, KeyboardInterrupt)
    stdscr.refresh.assert_called()


@pytest.mark.parametrize('ascii', [True, False])
def test_load_screen_initial_delay(terminal, stdscr, ascii):
    terminal.ascii = ascii

    # If we don't reach the initial delay nothing should be drawn
    with terminal.loader(delay=0.1):
        time.sleep(0.05)
    stdscr.subwin.addstr.assert_not_called()


@pytest.mark.parametrize('ascii', [True, False])
def test_load_screen_nested(terminal, ascii):
    terminal.ascii = ascii

    with terminal.loader(message='Outer'):
        with terminal.loader(message='Inner'):
            raise requests.ConnectionError()
        assert False  # Should never be reached

    assert isinstance(terminal.loader.exception, requests.ConnectionError)
    assert terminal.loader.depth == 0
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()


@pytest.mark.parametrize('ascii', [True, False])
def test_load_screen_nested_complex(terminal, stdscr, ascii):
    terminal.ascii = ascii

    with terminal.loader(message='Outer') as outer_loader:
        assert outer_loader.depth == 1

        with terminal.loader(message='Inner') as inner_loader:
            assert inner_loader.depth == 2
            assert inner_loader._args[2] == 'Outer'

        with terminal.loader():
            assert terminal.loader.depth == 2
            raise requests.ConnectionError()

        assert False  # Should never be reached

    assert isinstance(terminal.loader.exception, requests.ConnectionError)
    assert terminal.loader.depth == 0
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    error_message = 'Connection Error'.encode('ascii' if ascii else 'utf-8')
    stdscr.subwin.addstr.assert_called_once_with(1, 1, error_message)


def test_color(stdscr):

    colors = ['RED', 'GREEN', 'YELLOW', 'BLUE', 'MAGENTA', 'CYAN', 'WHITE']

    # Check that all colors start with the default value
    for color in colors:
        assert getattr(Color, color) == curses.A_NORMAL

    Color.init()
    assert curses.use_default_colors.called

    # Check that all colors are populated
    for color in colors:
        assert getattr(Color, color) == 23


def test_curses_session(stdscr):

    # Normal setup and cleanup
    with curses_session():
        pass
    assert curses.initscr.called
    assert curses.endwin.called
    curses.initscr.reset_mock()
    curses.endwin.reset_mock()

    # Ensure cleanup runs if an error occurs
    with pytest.raises(KeyboardInterrupt):
        with curses_session():
            raise KeyboardInterrupt()
    assert curses.initscr.called
    assert curses.endwin.called
    curses.initscr.reset_mock()
    curses.endwin.reset_mock()

    # But cleanup shouldn't run if stdscr was never instantiated
    curses.initscr.side_effect = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        with curses_session():
            pass
    assert curses.initscr.called
    assert not curses.endwin.called
    curses.initscr.reset_mock()
    curses.endwin.reset_mock()