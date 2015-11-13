# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from rtv.helpers import Navigator

try:
    from unittest import mock
except ImportError:
    import mock


def test_navigator_properties():

    def valid_page_cb(_):
        return

    nav = Navigator(valid_page_cb)
    assert nav.step == 1
    assert nav.position == (0, 0, False)
    assert nav.absolute_index == 0

    nav = Navigator(valid_page_cb, 5, 2, True)
    assert nav.step == -1
    assert nav.position == (5, 2, True)
    assert nav.absolute_index == 3


def test_navigator_move():

    def valid_page_cb(index):
        if index < 0 or index > 3:
            raise IndexError()

    nav = Navigator(valid_page_cb)

    # Try to scroll up past the first item
    valid, redraw = nav.move(-1, 2)
    assert not valid
    assert not redraw

    # Scroll down
    valid, redraw = nav.move(1, 3)
    assert nav.page_index == 0
    assert nav.cursor_index == 1
    assert valid
    assert not redraw

    # Scroll down, reach last item on the page and flip the screen
    valid, redraw = nav.move(1, 3)
    assert nav.page_index == 2
    assert nav.cursor_index == 0
    assert nav.inverted
    assert valid
    assert redraw

    # Keep scrolling
    valid, redraw = nav.move(1, 3)
    assert nav.page_index == 3
    assert nav.cursor_index == 0
    assert nav.inverted
    assert valid
    assert redraw

    # Reach the end of the page and stop
    valid, redraw = nav.move(1, 1)
    assert nav.page_index == 3
    assert nav.cursor_index == 0
    assert nav.inverted
    assert not valid
    assert not redraw

    # Last item was large and takes up the whole screen, scroll back up and
    # flip the screen again
    valid, redraw = nav.move(-1, 1)
    assert nav.page_index == 2
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert valid
    assert redraw


def test_navigator_move_new_submission():

    def valid_page_cb(index):
        if index != -1:
            raise IndexError()

    nav = Navigator(valid_page_cb, page_index=-1)

    # Can't move up
    valid, redraw = nav.move(-1, 1)
    assert nav.page_index == -1
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert not valid
    assert not redraw

    # Can't move down
    valid, redraw = nav.move(1, 1)
    assert nav.page_index == -1
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert not valid
    assert not redraw


def test_navigator_move_submission():

    def valid_page_cb(index):
        if index < -1 or index > 4:
            raise IndexError()

    nav = Navigator(valid_page_cb, page_index=-1)

    # Can't move up
    valid, redraw = nav.move(-1, 2)
    assert nav.page_index == -1
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert not valid
    assert not redraw

    # Moving down jumps to the first comment
    valid, redraw = nav.move(1, 2)
    assert nav.page_index == 0
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert valid
    assert redraw

    # Moving down again inverts the screen
    valid, redraw = nav.move(1, 2)
    assert nav.page_index == 1
    assert nav.cursor_index == 0
    assert nav.inverted
    assert valid
    assert redraw

    # Move up to the first comment
    valid, redraw = nav.move(-1, 2)
    assert nav.page_index == 0
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert valid
    assert redraw

    # Move up to the submission
    valid, redraw = nav.move(-1, 2)
    assert nav.page_index == -1
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert valid
    assert redraw


@pytest.mark.xfail(reason="Paging is still broken in several edge-cases")
def test_navigator_move_page():

    def valid_page_cb(index):
        if index < 0 or index > 7:
            raise IndexError()

    nav = Navigator(valid_page_cb, cursor_index=2)

    # Can't move up
    valid, redraw = nav.move_page(-1, 5)
    assert nav.page_index == 0
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert not valid
    assert not redraw

    # Page down
    valid, redraw = nav.move_page(1, 5)
    assert nav.page_index == 4
    assert nav.cursor_index == 0
    assert nav.inverted
    assert valid
    assert redraw

    # Page up
    valid, redraw = nav.move_page(-1, 3)
    assert nav.page_index == 2
    assert nav.cursor_index == 0
    assert not nav.inverted
    assert valid
    assert redraw


def test_navigator_flip():

    def valid_page_cb(index):
        if index < 0 or index > 10:
            raise IndexError()

    nav = Navigator(valid_page_cb)

    nav.flip(5)
    assert nav.page_index == 5
    assert nav.cursor_index == 5
    assert nav.inverted

    nav.flip(3)
    assert nav.page_index == 2
    assert nav.cursor_index == 3
    assert not nav.inverted