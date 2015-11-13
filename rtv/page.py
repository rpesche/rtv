import curses
import time
import sys
import logging

from kitchen.text.display import textual_width

from .docs import COMMENT_EDIT_FILE, SUBMISSION_FILE, HELP
from .helpers import open_editor, logged_in, Controller
from .terminal import Color, Terminal

_logger = logging.getLogger(__name__)


class BaseController(Controller):
    character_map = {}


class Page(Terminal):

    MIN_HEIGHT = 10
    MIN_WIDTH = 20

    def __init__(self, stdscr, reddit, config, oauth):

        super(Page, self).__init__(stdscr, config)

        self.reddit = reddit
        self.oauth = oauth
        self.content = None
        self.nav = None
        self.active = True

        self._header_window = None
        self._content_window = None
        self._subwindows = None

    def refresh_content(self, order=None):
        raise NotImplementedError

    @staticmethod
    def draw_item(window, data, inverted):
        raise NotImplementedError

    @BaseController.register('q')
    def exit(self):
        """
        Prompt to exit the application.
        """

        ch = self.prompt_input('Do you really want to quit? (y/n): ')
        if ch == 'y':
            sys.exit()
        elif ch != 'n':
            curses.flash()

    @BaseController.register('Q')
    def force_exit(self):
        sys.exit()

    @BaseController.register('?')
    def help(self):
        self.show_notification(HELP.strip().splitlines())

    @BaseController.register('1')
    def sort_content_hot(self):
        self.refresh_content(order='hot')

    @BaseController.register('2')
    def sort_content_top(self):
        self.refresh_content(order='top')

    @BaseController.register('3')
    def sort_content_rising(self):
        self.refresh_content(order='rising')

    @BaseController.register('4')
    def sort_content_new(self):
        self.refresh_content(order='new')

    @BaseController.register('5')
    def sort_content_controversial(self):
        self.refresh_content(order='controversial')

    @BaseController.register(curses.KEY_UP, 'k')
    def move_cursor_up(self):
        self._move_cursor(-1)
        self.clear_input_queue()

    @BaseController.register(curses.KEY_DOWN, 'j')
    def move_cursor_down(self):
        self._move_cursor(1)
        self.clear_input_queue()

    @BaseController.register('n', curses.KEY_NPAGE)
    def move_page_down(self):
        self._move_page(1)
        self.clear_input_queue()

    @BaseController.register('m', curses.KEY_PPAGE)
    def move_page_up(self):
        self._move_page(-1)
        self.clear_input_queue()

    @BaseController.register('a')
    @logged_in
    def upvote(self):
        data = self.content.get(self.nav.absolute_index)
        if 'likes' not in data:
            pass
        elif data['likes']:
            data['object'].clear_vote()
            data['likes'] = None
        else:
            data['object'].upvote()
            data['likes'] = True

    @BaseController.register('z')
    @logged_in
    def downvote(self):
        data = self.content.get(self.nav.absolute_index)
        if 'likes' not in data:
            pass
        elif data['likes'] or data['likes'] is None:
            data['object'].downvote()
            data['likes'] = False
        else:
            data['object'].clear_vote()
            data['likes'] = None

    @BaseController.register('u')
    def login(self):
        """
        Prompt to log into the user's account, or log out of the current
        account.
        """

        if self.reddit.is_oauth_session():
            ch = self.prompt_input('Log out? (y/n): ')
            if ch == 'y':
                self.oauth.clear_oauth_data()
                self.show_notification('Logged out')
            elif ch != 'n':
                curses.flash()
        else:
            self.oauth.authorize()

    @BaseController.register('d')
    @logged_in
    def delete(self):
        """
        Delete a submission or comment.
        """

        data = self.content.get(self.nav.absolute_index)
        if data.get('author') != self.reddit.user.name:
            curses.flash()
            return

        prompt = 'Are you sure you want to delete this? (y/n): '
        char = self.prompt_input(prompt)
        if char != 'y':
            self.show_notification('Aborted')
            return

        with self.loader(message='Deleting', delay=0):
            data['object'].delete()
            time.sleep(2.0)
        if self.loader.exception is None:
            self.refresh_content()

    @BaseController.register('e')
    @logged_in
    def edit(self):
        """
        Edit a submission or comment.
        """

        data = self.content.get(self.nav.absolute_index)
        if data.get('author') != self.reddit.user.name:
            curses.flash()
            return

        if data['type'] == 'Submission':
            subreddit = self.reddit.get_subreddit(self.content.name)
            content = data['text']
            info = SUBMISSION_FILE.format(content=content, name=subreddit)
        elif data['type'] == 'Comment':
            content = data['body']
            info = COMMENT_EDIT_FILE.format(content=content)
        else:
            curses.flash()
            return

        text = open_editor(info)
        if text == content:
            self.show_notification('Aborted')
            return

        with self.loader(message='Editing', delay=0):
            data['object'].edit(text)
            time.sleep(2.0)
        if self.loader.exception is None:
            self.refresh_content()

    @BaseController.register('i')
    @logged_in
    def get_inbox(self):
        """
        Checks the inbox for unread messages and displays a notification.
        """

        inbox = len(list(self.reddit.get_unread(limit=1)))
        message = 'New Messages' if inbox > 0 else 'No New Messages'
        self.show_notification(message)

    def clear_input_queue(self):
        """
        Clear excessive input caused by the scroll wheel or holding down a key
        """

        self.stdscr.nodelay(1)
        while self.stdscr.getch() != -1:
            continue
        self.stdscr.nodelay(0)

    def draw(self):

        n_rows, n_cols = self.stdscr.getmaxyx()
        if n_rows < self.MIN_HEIGHT or n_cols < self.MIN_WIDTH:
            return

        # Note: 2 argument form of derwin breaks PDcurses on Windows 7!
        self._header_window = self.stdscr.derwin(1, n_cols, 0, 0)
        self._content_window = self.stdscr.derwin(n_rows - 1, n_cols, 1, 0)

        self.stdscr.erase()
        self._draw_header()
        self._draw_content()
        self._add_cursor()

    def _draw_header(self):

        n_rows, n_cols = self._header_window.getmaxyx()

        self._header_window.erase()
        attr = curses.A_REVERSE | curses.A_BOLD | Color.CYAN
        self._header_window.bkgd(' ', attr)

        sub_name = self.content.name.replace('/r/front', 'Front Page')
        self.add_line(self._header_window, sub_name, 0, 0)
        if self.content.order is not None:
            order = ' [{}]'.format(self.content.order)
            self.add_line(self._header_window, order)

        if self.reddit.user is not None:
            username = self.reddit.user.name
            s_col = (n_cols - textual_width(username) - 1)
            # Only print username if it fits in the empty space on the right
            if (s_col - 1) >= textual_width(sub_name):
                self.add_line(self._header_window, username, 0, s_col)

        self._header_window.refresh()

    def _draw_content(self):
        """
        Loop through submissions and fill up the content page.
        """

        n_rows, n_cols = self._content_window.getmaxyx()
        self._content_window.erase()
        self._subwindows = []

        page_index, cursor_index, inverted = self.nav.position
        step = self.nav.step

        # If not inverted, align the first submission with the top and draw
        # downwards. If inverted, align the first submission with the bottom
        # and draw upwards.
        current_row = (n_rows - 1) if inverted else 0
        available_rows = (n_rows - 1) if inverted else n_rows
        for data in self.content.iterate(page_index, step, n_cols - 2):
            window_rows = min(available_rows, data['n_rows'])
            window_cols = n_cols - data['offset']
            start = current_row - window_rows if inverted else current_row
            subwindow = self._content_window.derwin(
                window_rows, window_cols, start, data['offset'])
            attr = self.draw_item(subwindow, data, inverted)
            self._subwindows.append((subwindow, attr))
            available_rows -= (window_rows + 1)  # Add one for the blank line
            current_row += step * (window_rows + 1)
            if available_rows <= 0:
                break
        else:
            # If the page is not full we need to make sure that it is NOT
            # inverted. Unfortunately, this currently means drawing the whole
            # page over again. Could not think of a better way to pre-determine
            # if the content will fill up the page, given that it is dependent
            # on the size of the terminal.
            if self.nav.inverted:
                self.nav.flip((len(self._subwindows) - 1))
                self._draw_content()

        self._content_window.refresh()

    def _add_cursor(self):
        self._edit_cursor(curses.A_REVERSE)

    def _remove_cursor(self):
        self._edit_cursor(curses.A_NORMAL)

    def _move_cursor(self, direction):
        self._remove_cursor()
        valid, redraw = self.nav.move(direction, len(self._subwindows))
        if not valid:
            curses.flash()

        # Note: ACS_VLINE doesn't like changing the attribute,
        # so always redraw.
        self._draw_content()
        self._add_cursor()

    def _move_page(self, direction):
        self._remove_cursor()
        valid, redraw = self.nav.move_page(direction, len(self._subwindows)-1)
        if not valid:
            curses.flash()

        # Note: ACS_VLINE doesn't like changing the attribute,
        # so always redraw.
        self._draw_content()
        self._add_cursor()

    def _edit_cursor(self, attribute=None):

        # Don't allow the cursor to go below page index 0
        if self.nav.absolute_index < 0:
            return

        # Don't allow the cursor to go over the number of subwindows
        # This could happen if the window is resized and the cursor index is
        # pushed out of bounds
        if self.nav.cursor_index >= len(self._subwindows):
            self.nav.cursor_index = len(self._subwindows)-1

        window, attr = self._subwindows[self.nav.cursor_index]
        if attr is not None:
            attribute |= attr

        n_rows, _ = window.getmaxyx()
        for row in range(n_rows):
            window.chgat(row, 0, 1, attribute)

        window.refresh()