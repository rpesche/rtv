import pytest

from rtv.config import Config
from rtv.terminal import Terminal

try:
    from unittest import mock
except ImportError:
    import mock


class MockStdscr(mock.MagicMock):

    def getyx(self):
        return self.y, self.x

    def getmaxyx(self):
        return self.nlines, self.ncols

    def derwin(self, *args):
        """
        derwin(begin_y, begin_x)
        derwin(nlines, ncols, begin_y, begin_x)
        """

        if len(args) == 2:
            nlines = self.nlines - args[0]
            ncols = self.ncols - args[1]
        else:
            nlines = min(self.nlines - args[2], args[0])
            ncols = min(self.ncols - args[3], args[1])
        subwin = MockStdscr(nlines=nlines, ncols=ncols, y=0, x=0)
        self.attach_mock(subwin, 'subwin')
        return subwin


@pytest.fixture(scope='module', params=[{'ascii': True}, {'ascii': False}],
                ids=['ascii', 'unicode'])
def config(request):
    return Config(**request.param)


@pytest.fixture(scope='function')
def stdscr():
    return MockStdscr(nlines=40, ncols=80, y=0, x=0)


@pytest.fixture(scope='function')
def terminal(stdscr, config):
    return Terminal(stdscr, config)