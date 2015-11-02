import six

from rtv.terminal import Terminal, LoadScreen, Color

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