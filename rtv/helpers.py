# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import curses
import codecs
import inspect
import webbrowser
import subprocess
from tempfile import NamedTemporaryFile

import six

from .exceptions import ProgramError


def logged_in(f):
    """
    Decorator for Page methods that require the user to be authenticated.
    """
    @wraps(f)
    def wrapped_method(self, *args, **kwargs):
        if not self.reddit.is_oauth_session():
            self.show_notification('Not logged in')
            return
        return f(self, *args, **kwargs)
    return wrapped_method


class Navigator(object):
    """
    Handles the math behind cursor movement and screen paging.

    This class determines how cursor movements effect the currently displayed
    page. For example, if scrolling down the page, items are drawn from the
    bottom up. This ensures that the item at the very bottom of the screen
    (the one selected by cursor) will be fully drawn and not cut off. Likewise,
    when scrolling up the page, items are drawn from the top down. If the
    cursor is moved around without hitting the top or bottom of the screen, the
    current mode is preserved.
    """

    def __init__(
            self,
            valid_page_cb,
            page_index=0,
            cursor_index=0,
            inverted=False):
        """
        Params:
            valid_page_callback (func): This function, usually `Content.get`,
                takes a page index and raises an IndexError if that index falls
                out of bounds. This is used to determine the upper and lower
                bounds of the page, i.e. when to stop scrolling.
            page_index (int): Initial page index.
            cursor_index (int): Initial cursor index, relative to the page.
            inverted (bool): Whether the page scrolling is reversed of not.
                normal - The page is drawn from the top of the screen,
                    starting with the page index, down to the bottom of
                    the screen.
                inverted - The page is drawn from the bottom of the screen,
                    starting with the page index, up to the top of the
                    screen.
        """

        self.page_index = page_index
        self.cursor_index = cursor_index
        self.inverted = inverted
        self._page_cb = valid_page_cb

    @property
    def step(self):
        return 1 if not self.inverted else -1

    @property
    def position(self):
        return self.page_index, self.cursor_index, self.inverted

    @property
    def absolute_index(self):
        """
        Return the index of the currently selected item.
        """

        return self.page_index + (self.step * self.cursor_index)

    def move(self, direction, n_windows):
        """
        Move the cursor up or down by the given increment.

        Params:
            direction (int): `1` will move the cursor down one item and `-1`
                will move the cursor up one item.
            n_windows (int): The number of items that are currently being drawn
                on the screen.

        Returns:
            valid (bool): Indicates whether or not the attempted cursor move is
                allowed. E.g. When the cursor is on the last comment,
                attempting to scroll down any further would not be valid.
            redraw (bool): Indicates whether or not the screen needs to be
                redrawn.
        """

        assert direction in (-1, 1)

        valid, redraw = True, False
        forward = ((direction * self.step) > 0)

        if forward:
            if self.page_index < 0:
                if self._is_valid(0):
                    # Special case - advance the page index if less than zero
                    self.page_index = 0
                    self.cursor_index = 0
                    redraw = True
                else:
                    valid = False
            else:
                self.cursor_index += 1
                if not self._is_valid(self.absolute_index):
                    # Move would take us out of bounds
                    self.cursor_index -= 1
                    valid = False
                elif self.cursor_index >= (n_windows - 1):
                    # Flip the orientation and reset the cursor
                    self.flip(self.cursor_index)
                    self.cursor_index = 0
                    redraw = True
        else:
            if self.cursor_index > 0:
                self.cursor_index -= 1
            else:
                self.page_index -= self.step
                if self._is_valid(self.absolute_index):
                    # We have reached the beginning of the page - move the
                    # index
                    redraw = True
                else:
                    self.page_index += self.step
                    valid = False  # Revert

        return valid, redraw

    def move_page(self, direction, n_windows):
        """
        Move the page down (positive direction) or up (negative direction).

        Paging down:
            The post on the bottom of the page becomes the post at the top of
            the page and the cursor is moved to the top.
        Paging up:
            The post at the top of the page becomes the post at the bottom of
            the page and the cursor is moved to the bottom.
        """

        assert direction in (-1, 1)
        assert n_windows >= 0

        # top of subreddit/submission page or only one
        # submission/reply on the screen: act as normal move
        if (self.absolute_index < 0) | (n_windows == 0):
            valid, redraw = self.move(direction, n_windows)
        else:
            # first page
            if self.absolute_index < n_windows and direction < 0:
                self.page_index = -1
                self.cursor_index = 0
                self.inverted = False

                # not submission mode: starting index is 0
                if not self._is_valid(self.absolute_index):
                    self.page_index = 0
                valid = True
            else:
                # flip to the direction of movement
                if ((direction > 0) & (self.inverted is True))\
                   | ((direction < 0) & (self.inverted is False)):
                    self.page_index += (self.step * (n_windows-1))
                    self.inverted = not self.inverted
                    self.cursor_index \
                        = (n_windows-(direction < 0)) - self.cursor_index

                valid = False
                adj = 0
                # check if reached the bottom
                while not valid:
                    n_move = n_windows - adj
                    if n_move == 0:
                        break

                    self.page_index += n_move * direction
                    valid = self._is_valid(self.absolute_index)
                    if not valid:
                        self.page_index -= n_move * direction
                        adj += 1

            redraw = True

        return valid, redraw

    def flip(self, n_windows):
        """
        Flip the orientation of the page.
        """

        assert n_windows >= 0
        self.page_index += (self.step * n_windows)
        self.cursor_index = n_windows
        self.inverted = not self.inverted

    def _is_valid(self, page_index):
        """
        Check if a page index will cause entries to fall outside valid range.
        """

        try:
            self._page_cb(page_index)
        except IndexError:
            return False
        else:
            return True


class Controller(object):
    """
    Event handler for triggering functions with curses keypresses.

    Register a keystroke to a class method using the @register decorator.
    >>> @Controller.register('a', 'A')
    >>> def func(self, *args)
    >>>     ...

    Register a default behavior by using `None`.
    >>> @Controller.register(None)
    >>> def default_func(self, *args)
    >>>     ...

    Bind the controller to a class instance and trigger a key. Additional
    arguments will be passed to the function.
    >>> controller = Controller(self)
    >>> controller.trigger('a', *args)
    """

    character_map = {}

    def __init__(self, instance):

        self.instance = instance
        # Build a list of parent controllers that follow the object's MRO to
        # check if any parent controllers have registered the keypress
        self.parents = inspect.getmro(type(self))[:-1]

    def trigger(self, char, *args, **kwargs):

        if isinstance(char, six.string_types) and len(char) == 1:
            char = ord(char)

        func = None
        # Check if the controller (or any of the controller's parents) have
        # registered a function to the given key
        for controller in self.parents:
            if func:
                break
            func = controller.character_map.get(char)
        # If the controller has not registered the key, check if there is a
        # default function registered
        for controller in self.parents:
            if func:
                break
            func = controller.character_map.get(None)
        return func(self.instance, *args, **kwargs) if func else None

    @classmethod
    def register(cls, *chars):
        def inner(f):
            for char in chars:
                if isinstance(char, six.string_types) and len(char) == 1:
                    cls.character_map[ord(char)] = f
                else:
                    cls.character_map[char] = f
            return f
        return inner


def open_editor(data=''):
    """
    Open a temporary file using the system's default editor.

    The data string will be written to the file before opening. This function
    will block until the editor has closed. At that point the file will be
    read and and lines starting with '#' will be stripped.
    """

    with NamedTemporaryFile(prefix='rtv-', suffix='.txt', mode='wb') as fp:
        fp.write(codecs.encode(data, 'utf-8'))
        fp.flush()
        editor = os.getenv('RTV_EDITOR') or os.getenv('EDITOR') or 'nano'

        curses.endwin()
        try:
            subprocess.Popen([editor, fp.name]).wait()
        except OSError:
            raise ProgramError('Could not open file with %s' % editor)
        curses.doupdate()

        # Open a second file object to read. This appears to be necessary in
        # order to read the changes made by some editors (gedit). w+ mode does
        # not work!
        with codecs.open(fp.name, 'utf-8') as fp2:
            text = ''.join(line for line in fp2 if not line.startswith('#'))
            text = text.rstrip()

    return text


def open_browser(url, display=True):
    """
    Open the given url using the default webbrowser. The preferred browser can
    specified with the $BROWSER environment variable. If not specified, python
    webbrowser will try to determine the default to use based on your system.

    For browsers requiring an X display, we call webbrowser.open_new_tab(url)
    and redirect stdout/stderr to devnull. This is a workaround to stop firefox
    from spewing warning messages to the console. See
    http://bugs.python.org/issue22277 for a better description of the problem.

    For console browsers (e.g. w3m), RTV will suspend and display the browser
    window within the same terminal. This mode is triggered either when
    1. $BROWSER is set to a known console browser, or
    2. $DISPLAY is undefined, indicating that the terminal is running headless

    There may be other cases where console browsers are opened (xdg-open?) but
    are not detected here.
    """

    if display:
        command = "import webbrowser; webbrowser.open_new_tab('%s')" % url
        args = [sys.executable, '-c', command]
        with open(os.devnull, 'ab+', 0) as null:
            subprocess.check_call(args, stdout=null, stderr=null)
    else:
        curses.endwin()
        webbrowser.open_new_tab(url)
        curses.doupdate()