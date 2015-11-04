# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import praw
import pytest

from rtv.config import Config
from rtv.terminal import Terminal
from rtv.oauth import OAuthHelper

try:
    from unittest import mock
except ImportError:
    import mock


class MockStdscr(mock.MagicMock):
    """
    Extend mock to mimic curses.stdscr by keeping track of the terminal
    coordinates and allowing for the creation of subwindows with the same
    properties as stdscr.
    """

    def getyx(self):
        return self.y, self.x

    def getmaxyx(self):
        return self.nlines, self.ncols

    def derwin(self, *args):
        """
        derwin()
        derwin(begin_y, begin_x)
        derwin(nlines, ncols, begin_y, begin_x)
        """

        if 'subwin' not in dir(self):
            self.attach_mock(MockStdscr(), 'subwin')

        if len(args) == 0:
            nlines = self.nlines
            ncols = self.ncols
        elif len(args) == 2:
            nlines = self.nlines - args[0]
            ncols = self.ncols - args[1]
        else:
            nlines = min(self.nlines - args[2], args[0])
            ncols = min(self.ncols - args[3], args[1])

        self.subwin.nlines = nlines
        self.subwin.ncols = ncols
        self.subwin.x = 0
        self.subwin.y = 0
        return self.subwin


@pytest.fixture(params=[{'ascii': True}, {'ascii': False}])
def config(request):
    return Config(**request.param)


@pytest.fixture()
def stdscr():
    return MockStdscr(nlines=40, ncols=80, x=0, y=0)


@pytest.fixture()
def terminal(stdscr, config):
    return Terminal(stdscr, ascii=config['ascii'])


@pytest.fixture()
def reddit():
    return praw.Reddit(user_agent='rtv test suite', decode_html_entities=False)


@pytest.fixture()
def oauth(reddit, terminal, config):
    return OAuthHelper(reddit, terminal, config)