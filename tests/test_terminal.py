# -*- coding: utf-8 -*-

import six

from rtv.docs import HELP
from rtv.terminal import Terminal, LoadScreen, Color
from rtv.config import Config

try:
    from unittest import mock
except ImportError:
    import mock


def test_terminal_properties(config, stdscr):

    terminal = Terminal(stdscr, config)

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


def test_terminal_clean_ascii(stdscr):

    config = Config(ascii=True)
    terminal = Terminal(stdscr, config)

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


def test_terminal_clean_utf8(stdscr):

    config = Config(ascii=False)
    terminal = Terminal(stdscr, config)

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


def test_terminal_clean_ncols(stdscr):

    config = Config(ascii=False)
    terminal = Terminal(stdscr, config)

    text = terminal.clean(u'hello', n_cols=5)
    assert text.decode('utf-8') == u'hello'
    text = terminal.clean(u'hello', n_cols=4)
    assert text.decode('utf-8') == u'hell'
    text = terminal.clean(u'ｈｅｌｌｏ', n_cols=10)
    assert text.decode('utf-8') == u'ｈｅｌｌｏ'
    text = terminal.clean(u'ｈｅｌｌｏ', n_cols=9)
    assert text.decode('utf-8') == u'ｈｅｌｌ'


def test_terminal_add_line(stdscr, config):

    terminal = Terminal(stdscr, config)

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


def test_show_notification(stdscr, config):

    terminal = Terminal(stdscr, config)

    terminal.show_notification(HELP)