# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import time
import curses
import weakref
import logging
import threading
import webbrowser
import curses.ascii
from curses import textpad
from contextlib import contextmanager

import six
import praw
import requests
from kitchen.text.display import textual_width_chop

from .exceptions import EscapeInterrupt

_logger = logging.getLogger(__name__)


class Terminal(object):

    # ASCII code
    ESCAPE = 27
    RETURN = 10

    def __init__(self, stdscr, ascii=False):

        self.stdscr = stdscr
        self.ascii = ascii
        self.loader = LoadScreen(self)

        self._display = None

    @property
    def up_arrow(self):
        symbol = '^' if self.ascii else '▲'
        attr = curses.A_BOLD | Color.GREEN
        return symbol, attr

    @property
    def down_arrow(self):
        symbol = 'v' if self.ascii else '▼'
        attr = curses.A_BOLD | Color.RED
        return symbol, attr

    @property
    def neutral_arrow(self):
        symbol = 'o' if self.ascii else '•'
        attr = curses.A_BOLD
        return symbol, attr

    @property
    def guilded(self):
        symbol = '*' if self.ascii else '✪'
        attr = curses.A_BOLD | Color.YELLOW
        return symbol, attr

    @property
    def display(self):
        """
        Use a number of methods to guess if the default webbrowser will open in
        the background as opposed to opening directly in the terminal.
        """

        if self._display is None:
            display = bool(os.environ.get("DISPLAY"))
            # Use the convention defined here to parse $BROWSER
            # https://docs.python.org/2/library/webbrowser.html
            console_browsers = ['www-browser', 'links', 'links2', 'elinks',
                                'lynx', 'w3m']
            if "BROWSER" in os.environ:
                user_browser = os.environ["BROWSER"].split(os.pathsep)[0]
                if user_browser in console_browsers:
                    display = False
            if webbrowser._tryorder:
                if webbrowser._tryorder[0] in console_browsers:
                    display = False
            self._display = display
        return self._display

    def get_arrow(self, likes):
        """
        Curses does define constants for symbols (e.g. curses.ACS_BULLET).
        However, they rely on using the curses.addch() function, which has been
        found to be buggy and a general PITA to work with. By defining them as
        unicode points they can be added via the more reliable curses.addstr().
        http://bugs.python.org/issue21088
        """

        if likes is None:
            return self.neutral_arrow
        elif likes:
            return self.up_arrow
        else:
            return self.down_arrow

    def clean(self, string, n_cols=None):
        """
        Required reading!
            http://nedbatchelder.com/text/unipain.html

        Python 2 input string will be a unicode type (unicode code points).
        Curses will accept unicode if all of the points are in the ascii range.
        However, if any of the code points are not valid ascii curses will
        throw a UnicodeEncodeError: 'ascii' codec can't encode character,
        ordinal not in range(128). If we encode the unicode to a utf-8 byte
        string and pass that to curses, it will render correctly.

        Python 3 input string will be a string type (unicode code points).
        Curses will accept that in all cases. However, the n character count in
        addnstr will not be correct. If code points are passed to addnstr,
        curses will treat each code point as one character and will not account
        for wide characters. If utf-8 is passed in, addnstr will treat each
        'byte' as a single character.
        """

        if n_cols is not None and n_cols <= 0:
            return ''

        if self.ascii:
            if isinstance(string, six.binary_type):
                string = string.decode('utf-8')
            string = string.encode('ascii', 'replace')
            return string[:n_cols] if n_cols else string
        else:
            if n_cols:
                string = textual_width_chop(string, n_cols)
            if isinstance(string, six.text_type):
                string = string.encode('utf-8')
            return string

    def add_line(self, window, text, row=None, col=None, attr=None):
        """
        Unicode aware version of curses's built-in addnstr method.

        Safely draws a line of text on the window starting at position
        (row, col). Checks the boundaries of the window and cuts off the text
        if it exceeds the length of the window.
        """

        # The following arg combos must be supported to conform with addnstr
        # (window, text)
        # (window, text, attr)
        # (window, text, row, col)
        # (window, text, row, col, attr)

        cursor_row, cursor_col = window.getyx()
        row = row if row is not None else cursor_row
        col = col if col is not None else cursor_col

        max_rows, max_cols = window.getmaxyx()
        n_cols = max_cols - col - 1
        if n_cols <= 0:
            # Trying to draw outside of the screen bounds
            return

        text = self.clean(text, n_cols)
        params = [] if attr is None else [attr]
        window.addstr(row, col, text, *params)

    def show_notification(self, message):
        """
        Overlay a message box on the center of the screen and wait for input.

        Params:
            message (list or string): List of strings, one per line.
        """

        if isinstance(message, six.string_types):
            message = [message]

        n_rows, n_cols = self.stdscr.getmaxyx()

        box_width = max(map(len, message)) + 2
        box_height = len(message) + 2

        # Cut off the lines of the message that don't fit on the screen
        box_width = min(box_width, n_cols)
        box_height = min(box_height, n_rows)
        message = message[:box_height-2]

        s_row = (n_rows - box_height) // 2
        s_col = (n_cols - box_width) // 2

        window = self.stdscr.derwin(box_height, box_width, s_row, s_col)
        window.erase()
        window.border()

        for index, line in enumerate(message, start=1):
            self.add_line(window, line, index, 1)
        window.refresh()
        ch = self.stdscr.getch()

        window.clear()
        del window
        self.stdscr.refresh()

        return ch

    def text_input(self, window, allow_resize=False):
        """
        Transform a window into a text box that will accept user input and loop
        until an escape sequence is entered.

        If the escape key (27) is pressed, cancel the textbox and return None.
        Otherwise, the textbox will wait until it is full (^j, or a new line is
        entered on the bottom line) or the BEL key (^g) is pressed.
        """

        window.clear()

        # Set cursor mode to 1 because 2 doesn't display on some terminals
        curses.curs_set(1)

        # Keep insert_mode off to avoid the recursion error described here
        # http://bugs.python.org/issue13051
        textbox = textpad.Textbox(window)
        textbox.stripspaces = 0

        def validate(ch):
            "Filters characters for special key sequences"
            if ch == self.ESCAPE:
                raise EscapeInterrupt()
            if (not allow_resize) and (ch == curses.KEY_RESIZE):
                raise EscapeInterrupt()
            # Fix backspace for iterm
            if ch == curses.ascii.DEL:
                ch = curses.KEY_BACKSPACE
            return ch

        # Wrapping in an exception block so that we can distinguish when the
        # user hits the return character from when the user tries to back out
        # of the input.
        try:
            out = textbox.edit(validate=validate)
            if isinstance(out, six.binary_type):
                out = out.decode('utf-8')
        except EscapeInterrupt:
            out = None

        curses.curs_set(0)
        return self.strip_textpad(out)

    def prompt_input(self, prompt, key=False):
        """
        Display a text prompt at the bottom of the screen.

        Params:
            prompt (string): Text prompt that will be displayed
            key (bool): If true, grab a single keystroke instead of a full
                        string. This can be faster than pressing enter for
                        single key prompts (e.g. y/n?)
        """

        n_rows, n_cols = self.stdscr.getmaxyx()
        attr = curses.A_BOLD | Color.CYAN
        prompt = self.clean(prompt, n_cols - 1)
        window = self.stdscr.derwin(
            1, n_cols - len(prompt), n_rows - 1, len(prompt))
        window.attrset(attr)
        self.add_line(self.stdscr, prompt, n_rows-1, 0, attr)
        self.stdscr.refresh()
        if key:
            curses.curs_set(1)
            ch = self.stdscr.getch()
            # Can't convert ch to unicode because it may be an arbitrary
            # keyboard code, e.g. F1, that doesn't map through six.unichr
            text = ch if ch != self.ESCAPE else None
            curses.curs_set(0)
        else:
            text = self.text_input(window)
        return text

    @staticmethod
    def strip_textpad(text):
        """
        Attempt to intelligently strip excess whitespace from the output of a
        curses textpad.
        """

        if text is None:
            return text

        # Trivial case where the textbox is only one line long.
        if '\n' not in text:
            return text.rstrip()

        # Allow one space at the end of the line. If there is more than one
        # space, assume that a newline operation was intended by the user
        stack, current_line = [], ''
        for line in text.split('\n'):
            if line.endswith('  '):
                stack.append(current_line + line.rstrip())
                current_line = ''
            else:
                current_line += line
        stack.append(current_line)

        # Prune empty lines at the bottom of the textbox.
        for item in stack[::-1]:
            if len(item) == 0:
                stack.pop()
            else:
                break

        out = '\n'.join(stack)
        return out


class LoadScreen(object):
    """
    Display a loading dialog while waiting for a blocking action to complete.

    This class spins off a separate thread to animate the loading screen in the
    background. The loading thread also takes control of stdscr.getch(). If
    an exception occurs in the main thread while the loader is active, the
    exception will be caught, attached to the loader object, and displayed as
    a notification. The attached exception can be used to trigger context
    sensitive actions. For example, if the connection hangs while opening a
    submission, the user may press ctrl-c to raise a KeyboardInterrupt. In this
    case we would *not* want to refresh the current page.

    Usage:
        >>> with self.terminal.loader(...) as loader:
        >>>     # Perform a blocking request to load content
        >>>     blocking_request(...)
        >>>
        >>> if loader.exception is None:
        >>>     # Only run this if the load was successful
        >>>     self.refresh_content()
    """

    def __init__(self, terminal):

        self.exception = None
        self._terminal = weakref.proxy(terminal)
        self._args = None
        self._animator = None
        self._is_running = None

    def __call__(self, delay=0.5, interval=0.4, message='Downloading',
                 trail='...'):
        """
        Params:
            delay (float): Length of time that the loader will wait before
                printing on the screen. Used to prevent flicker on pages that
                load very fast.
            interval (float): Length of time between each animation frame.
            message (str): Message to display
            trail (str): Trail of characters that will be animated by the
                loading screen.
        """

        self.exception = None
        self._args = (delay, interval, message, trail)
        return self

    def __enter__(self):

        self._animator = threading.Thread(target=self.animate, args=self._args)
        self._animator.daemon = True

        self._is_running = True
        self._animator.start()
        return self

    def __exit__(self, exc_type, e, exc_tb):

        self._is_running = False
        self._animator.join()
        self._terminal.stdscr.refresh()

        if isinstance(e, praw.errors.APIException):
            message = ['Error: {}'.format(e.error_type), e.message]
            self._terminal.show_notification(message)
            self.exception = e
            _logger.exception(e)
            return True
        elif isinstance(e, praw.errors.ClientException):
            message = ['Error: Client Exception', e.message]
            self._terminal.show_notification(message)
            self.exception = e
            _logger.exception(e)
            return True
        elif isinstance(e, requests.HTTPError):
            self._terminal.show_notification('Unexpected Error')
            self.exception = e
            _logger.exception(e)
            return True
        elif isinstance(e, requests.ConnectionError):
            self._terminal.show_notification('Unexpected Error')
            self.exception = e
            _logger.exception(e)
            return True
        elif isinstance(e, KeyboardInterrupt):
            self.exception = e
            return True

    def animate(self, delay, interval, message, trail):

        start = time.time()
        while (time.time() - start) < delay:
            if not self._is_running:
                return
            time.sleep(0.01)

        message_len = len(message) + len(trail)
        n_rows, n_cols = self._terminal.stdscr.getmaxyx()
        s_row = (n_rows - 3) // 2
        s_col = (n_cols - message_len - 1) // 2
        window = self._terminal.stdscr.derwin(3, message_len + 2, s_row, s_col)

        while True:
            for i in range(len(trail) + 1):
                if not self._is_running:
                    window.clear()
                    del window
                    return

                window.erase()
                window.border()
                self._terminal.add_line(window, message + trail[:i], 1, 1)
                window.refresh()
                time.sleep(interval)


class Color(object):

    """
    Color attributes for curses.
    """

    RED = curses.A_NORMAL
    GREEN = curses.A_NORMAL
    YELLOW = curses.A_NORMAL
    BLUE = curses.A_NORMAL
    MAGENTA = curses.A_NORMAL
    CYAN = curses.A_NORMAL
    WHITE = curses.A_NORMAL

    _colors = {
        'RED': (curses.COLOR_RED, -1),
        'GREEN': (curses.COLOR_GREEN, -1),
        'YELLOW': (curses.COLOR_YELLOW, -1),
        'BLUE': (curses.COLOR_BLUE, -1),
        'MAGENTA': (curses.COLOR_MAGENTA, -1),
        'CYAN': (curses.COLOR_CYAN, -1),
        'WHITE': (curses.COLOR_WHITE, -1),
    }

    @classmethod
    def init(cls):
        """
        Initialize color pairs inside of curses using the default background.

        This should be called once during the curses initial setup. Afterwards,
        curses color pairs can be accessed directly through class attributes.
        """

        # Assign the terminal's default (background) color to code -1
        curses.use_default_colors()

        for index, (attr, code) in enumerate(cls._colors.items(), start=1):
            curses.init_pair(index, code[0], code[1])
            setattr(cls, attr, curses.color_pair(index))

    @classmethod
    def get_level(cls, level):

        levels = [cls.MAGENTA, cls.CYAN, cls.GREEN, cls.YELLOW]
        return levels[level % len(levels)]


@contextmanager
def curses_session():
    """
    Setup terminal and initialize curses. Most of this copied from
    curses.wrapper in order to convert the wrapper into a context manager.
    """

    try:
        # Curses must wait for some time after the Escape key is pressed to
        # check if it is the beginning of an escape sequence indicating a
        # special key. The default wait time is 1 second, which means that
        # http://stackoverflow.com/questions/27372068
        os.environ['ESCDELAY'] = '25'

        # Initialize curses
        stdscr = curses.initscr()

        # Turn off echoing of keys, and enter cbreak mode, where no buffering
        # is performed on keyboard input
        curses.noecho()
        curses.cbreak()

        # In keypad mode, escape sequences for special keys (like the cursor
        # keys) will be interpreted and a special value like curses.KEY_LEFT
        # will be returned
        stdscr.keypad(1)

        # Start color, too.  Harmless if the terminal doesn't have color; user
        # can test with has_color() later on.  The try/catch works around a
        # minor bit of over-conscientiousness in the curses module -- the error
        # return from C start_color() is ignorable.
        try:
            curses.start_color()
        except:
            pass

        # Hide the blinking cursor
        curses.curs_set(0)

        Color.init()

        yield stdscr

    finally:
        if 'stdscr' not in locals():
            stdscr.keypad(0)
            curses.echo()
            curses.nocbreak()
            curses.endwin()