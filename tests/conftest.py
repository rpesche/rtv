import pytest

from rtv.config import Config

try:
    from unittest import mock
except ImportError:
    import mock

@pytest.fixture(scope='module', params=[{'ascii': True}, {'ascii': False}],
                ids=['ascii', 'unicode'])
def config(request):
    return Config(**request.param)

@pytest.fixture(scope='function')
def stdscr():

    class MockWindow(mock.Mock):

        def __new__(cls, *args, **kwargs):
            window = super(MockWindow, cls).__new__(cls, *args, **kwargs)

            # window.getmaxyx.return_value = window.nlines, window.ncols
            # window.getyx.return_value = window.y, window.x
            # window.getch.return_value = 10
            return window

        def derwin(self, *args):
            """
            derwin(begin_y, begin_x)
            derwin(nlines, ncols, begin_y, begin_x)
            """

            if len(args) == 2:
                nlines = self.nlines - args[0]
                ncols = self.ncols - args[1]
            else:
                nlines = min(self.nlines, args[0]) - args[2]
                ncols = min(self.ncols, args[1]) - args[3]
            return MockWindow(nlines=nlines, ncols=ncols, y=0, x=0)

    stdscr = MockWindow(nlines=40, ncols=80, y=0, x=0)
    return stdscr