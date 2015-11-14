# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import curses

import pytest

from rtv.objects import Color, LoadScreen, curses_session


@pytest.mark.parametrize('ascii', [True, False])
def test_load_screen(terminal, stdscr, ascii):

    terminal.ascii = ascii
    window = stdscr.derwin()

    # Ensure the thread is properly started/stopped
    with terminal.loader(delay=0, message=u'Hello', trail=u'...'):
        assert terminal.loader._animator.is_alive()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert terminal.loader.exception is None
    assert window.ncols == 10
    assert window.nlines == 3
    stdscr.refresh.assert_called()
    stdscr.reset_mock()

    # Raising an exception should clean up the loader properly
    with pytest.raises(Exception):
        with terminal.loader(delay=0):
            assert terminal.loader._animator.is_alive()
            raise Exception()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    stdscr.refresh.assert_called()
    stdscr.reset_mock()

    # Raising a handled exception should get stored on the loaders
    with terminal.loader(delay=0):
        assert terminal.loader._animator.is_alive()
        raise KeyboardInterrupt()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert isinstance(terminal.loader.exception, KeyboardInterrupt)
    stdscr.refresh.assert_called()
    stdscr.reset_mock()

    # If we don't reach the initial delay nothing should be drawn
    with terminal.loader(delay=0.1):
        time.sleep(0.05)
    window.addstr.assert_not_called()
    window.reset_mock()


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