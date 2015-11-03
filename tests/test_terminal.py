# -*- coding: utf-8 -*-
import curses

import six

from rtv.docs import HELP

try:
    from unittest import mock
except ImportError:
    import mock


def test_terminal_properties(terminal):

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
    with mock.patch.dict('os.environ', {'DISPLAY': 'term', 'BROWSER': 'w3m'}):
        assert terminal.display is False

    terminal._display = None
    with mock.patch.dict('os.environ', {'DISPLAY': 'term', 'BROWSER': ''}):
        assert terminal.display is True

    assert terminal.get_arrow(None) is not None
    assert terminal.get_arrow(True) is not None
    assert terminal.get_arrow(False) is not None


def test_terminal_clean(terminal):

    if terminal.config['ascii']:
        # unicode returns ascii
        text = terminal.clean(u'hello ❤')
        assert isinstance(text, six.binary_type)
        assert text.decode('ascii') == u'hello ?'
        # utf-8 returns ascii
        text = terminal.clean(u'hello ❤'.encode('utf-8'))
        assert isinstance(text, six.binary_type)
        assert text.decode('ascii') == u'hello ?'
        # ascii returns ascii
        text = terminal.clean(u'hello'.encode('ascii'))
        assert isinstance(text, six.binary_type)
        assert text.decode('ascii') == u'hello'
    else:
        # unicode returns utf-8
        text = terminal.clean(u'hello ❤')
        assert isinstance(text, six.binary_type)
        assert text.decode('utf-8') == u'hello ❤'
        # utf-8 returns utf-8
        text = terminal.clean(u'hello ❤'.encode('utf-8'))
        assert isinstance(text, six.binary_type)
        assert text.decode('utf-8') == u'hello ❤'
        # ascii returns utf-8
        text = terminal.clean(u'hello'.encode('ascii'))
        assert isinstance(text, six.binary_type)
        assert text.decode('utf-8') == u'hello'


def test_terminal_clean_ncols(terminal):

    if not terminal.config['ascii']:
        text = terminal.clean(u'hello', n_cols=5)
        assert text.decode('utf-8') == u'hello'
        text = terminal.clean(u'hello', n_cols=4)
        assert text.decode('utf-8') == u'hell'
        text = terminal.clean(u'ｈｅｌｌｏ', n_cols=10)
        assert text.decode('utf-8') == u'ｈｅｌｌｏ'
        text = terminal.clean(u'ｈｅｌｌｏ', n_cols=9)
        assert text.decode('utf-8') == u'ｈｅｌｌ'


def test_terminal_add_line(terminal, stdscr):

    terminal.add_line(stdscr, u'hello')
    assert stdscr.addstr.called_with(0, 0, u'hello'.encode('ascii'))
    stdscr.reset_mock()

    # Text will be drawn, but cut off to fit on the screen
    terminal.add_line(stdscr, u'hello', row=3, col=75)
    assert stdscr.addstr.called_with((3, 75, u'hell'.encode('ascii')))
    stdscr.reset_mock()

    # Outside of screen bounds, don't even try to draw the text
    terminal.add_line(stdscr, u'hello', col=79)
    assert stdscr.addstr.assert_not_called()
    stdscr.reset_mock()


def test_show_notification(terminal, stdscr):

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


def test_text_input(terminal, stdscr):

    stdscr.nlines = 1
    with mock.patch('curses.curs_set'):
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