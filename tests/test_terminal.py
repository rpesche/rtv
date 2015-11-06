# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import curses

import six
import pytest

from rtv.docs import HELP
from rtv.terminal import LoadScreen, Color, curses_session

try:
    from unittest import mock
except ImportError:
    import mock


def test_terminal_properties(terminal, config):

    assert len(terminal.up_arrow) == 2
    assert isinstance(terminal.up_arrow[0], six.text_type)
    assert len(terminal.down_arrow) == 2
    assert isinstance(terminal.down_arrow[0], six.text_type)
    assert len(terminal.neutral_arrow) == 2
    assert isinstance(terminal.neutral_arrow[0], six.text_type)
    assert len(terminal.guilded) == 2
    assert isinstance(terminal.guilded[0], six.text_type)

    terminal._display = None
    with mock.patch.dict('os.environ', {'DISPLAY': ''}):
        assert terminal.display is False

    terminal._display = None
    with mock.patch.dict('os.environ', {'DISPLAY': ':0', 'BROWSER': 'w3m'}):
        assert terminal.display is False

    terminal._display = None
    with mock.patch.dict('os.environ', {'DISPLAY': ':0', 'BROWSER': ''}), \
            mock.patch('webbrowser._tryorder'):
        assert terminal.display is True

    assert terminal.get_arrow(None) is not None
    assert terminal.get_arrow(True) is not None
    assert terminal.get_arrow(False) is not None
    assert terminal.ascii == config['ascii']
    assert isinstance(terminal.loader, LoadScreen)


def test_terminal_clean_ascii(terminal):

    terminal.ascii = True

    # unicode returns ascii
    text = terminal.clean('hello ❤')
    assert isinstance(text, six.binary_type)
    assert text.decode('ascii') == 'hello ?'

    # utf-8 returns ascii
    text = terminal.clean('hello ❤'.encode('utf-8'))
    assert isinstance(text, six.binary_type)
    assert text.decode('ascii') == 'hello ?'

    # ascii returns ascii
    text = terminal.clean('hello'.encode('ascii'))
    assert isinstance(text, six.binary_type)
    assert text.decode('ascii') == 'hello'


def test_terminal_clean_unicode(terminal):

    terminal.ascii = False

    # unicode returns utf-8
    text = terminal.clean('hello ❤')
    assert isinstance(text, six.binary_type)
    assert text.decode('utf-8') == 'hello ❤'

    # utf-8 returns utf-8
    text = terminal.clean('hello ❤'.encode('utf-8'))
    assert isinstance(text, six.binary_type)
    assert text.decode('utf-8') == 'hello ❤'

    # ascii returns utf-8
    text = terminal.clean('hello'.encode('ascii'))
    assert isinstance(text, six.binary_type)
    assert text.decode('utf-8') == 'hello'


def test_terminal_clean_ncols(terminal):

    text = terminal.clean('hello', n_cols=5)
    assert text.decode('utf-8') == 'hello'

    text = terminal.clean('hello', n_cols=4)
    assert text.decode('utf-8') == 'hell'

    text = terminal.clean('ｈｅｌｌｏ', n_cols=10)
    assert text.decode('utf-8') == 'ｈｅｌｌｏ'

    text = terminal.clean('ｈｅｌｌｏ', n_cols=9)
    assert text.decode('utf-8') == 'ｈｅｌｌ'


@pytest.mark.parametrize('ascii', [True, False])
def test_terminal_add_line(terminal, stdscr, ascii):

    terminal.ascii = ascii

    terminal.add_line(stdscr, 'hello')
    assert stdscr.addstr.called_with(0, 0, 'hello'.encode('ascii'))
    stdscr.reset_mock()

    # Text will be drawn, but cut off to fit on the screen
    terminal.add_line(stdscr, 'hello', row=3, col=75)
    assert stdscr.addstr.called_with((3, 75, 'hell'.encode('ascii')))
    stdscr.reset_mock()

    # Outside of screen bounds, don't even try to draw the text
    terminal.add_line(stdscr, 'hello', col=79)
    assert stdscr.addstr.assert_not_called()
    stdscr.reset_mock()


@pytest.mark.parametrize('ascii', [True, False])
def test_show_notification(terminal, stdscr, ascii):

    terminal.ascii = ascii

    # The whole message should fit in 40x80
    text = HELP.strip().splitlines()
    terminal.show_notification(text)
    assert stdscr.subwin.nlines == len(text) + 2
    assert stdscr.subwin.ncols == 80
    assert stdscr.subwin.addstr.call_count == len(text)
    stdscr.reset_mock()

    # The text should be trimmed to fit in 20x20
    stdscr.nlines, stdscr.ncols = 15, 20
    text = HELP.strip().splitlines()
    terminal.show_notification(text)
    assert stdscr.subwin.nlines == 15
    assert stdscr.subwin.ncols == 20
    assert stdscr.subwin.addstr.call_count == 13


@pytest.mark.parametrize('ascii', [True, False])
def test_text_input(terminal, stdscr, ascii):

    terminal.ascii = ascii
    stdscr.nlines = 1

    # Text will be wrong because stdscr.inch() is not implemented
    # But we can at least tell if text was captured or not
    stdscr.getch.side_effect = ['h', 'i', '!', terminal.RETURN]
    assert isinstance(terminal.text_input(stdscr), six.text_type)

    stdscr.getch.side_effect = ['b', 'y', 'e', terminal.ESCAPE]
    assert terminal.text_input(stdscr) is None

    stdscr.getch.side_effect = ['h', curses.KEY_RESIZE, terminal.RETURN]
    assert terminal.text_input(stdscr, allow_resize=True) is not None

    stdscr.getch.side_effect = ['h', curses.KEY_RESIZE, terminal.RETURN]
    assert terminal.text_input(stdscr, allow_resize=False) is None


@pytest.mark.parametrize('ascii', [True, False])
def test_prompt_input(terminal, stdscr, ascii):

    terminal.ascii = ascii
    window = stdscr.derwin()

    window.getch.side_effect = ['h', 'e', 'l', 'l', 'o', terminal.RETURN]
    assert isinstance(terminal.prompt_input('hi'), six.text_type)

    stdscr.addstr.assert_called_with(39, 0, 'hi'.encode('ascii'), 2097152)
    assert window.nlines == 1
    assert window.ncols == 78

    window.getch.side_effect = ['b', 'y', 'e', terminal.ESCAPE]
    assert terminal.prompt_input('hi') is None

    stdscr.getch.side_effect = ['b', 'e', 'l', 'l', 'o', terminal.RETURN]
    assert terminal.prompt_input('hi', key=True) == 'b'

    stdscr.getch.side_effect = [terminal.ESCAPE, 'e', 'l', 'l', 'o']
    assert terminal.prompt_input('hi', key=True) is None


@pytest.mark.parametrize('ascii', [True, False])
def test_load_screen(terminal, stdscr, ascii):

    terminal.ascii = ascii
    window = stdscr.derwin()

    # Ensure the thread is properly started/stopped
    with terminal.loader(delay=0, message=u'Hello', trail=u'...'):
        assert terminal.loader._animator.is_alive()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
    assert window.ncols == 10
    assert window.nlines == 3
    stdscr.refresh.assert_called()
    stdscr.reset_mock()

    # Raising and exception should clean up the loader properly
    with pytest.raises(Exception):
        with terminal.loader(delay=0):
            assert terminal.loader._animator.is_alive()
            raise Exception()
    assert not terminal.loader._is_running
    assert not terminal.loader._animator.is_alive()
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
