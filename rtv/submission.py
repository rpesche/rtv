# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import curses

from .content import SubmissionContent
from .page import Page, PageController, logged_in
from .objects import Navigator, Color
from .terminal import Terminal
from .docs import COMMENT_FILE


class SubmissionController(PageController):
    character_map = {}


class SubmissionPage(Page):

    def __init__(self, reddit, term, config, oauth, url=None, submission=None):
        super(SubmissionPage, self).__init__(reddit, term, config, oauth)

        if url:
            self.content = SubmissionContent.from_url(reddit, url, term.loader)
        else:
            self.content = SubmissionContent(submission, term.loader)

        self.controller = SubmissionController(self)
        # Start at the submission post, which is indexed as -1
        self.nav = Navigator(self.content.get, page_index=-1)

    @SubmissionController.register(curses.KEY_RIGHT, 'l', ' ')
    def toggle_comment(self):
        "Toggle the selected comment tree between visible and hidden"

        current_index = self.nav.absolute_index
        self.content.toggle(current_index)
        if self.nav.inverted:
            # Reset the navigator so that the cursor is at the bottom of the
            # page. This is a workaround to handle if folding the comment
            # causes the cursor index to go out of bounds.
            self.nav.page_index, self.nav.cursor_index = current_index, 0

    @SubmissionController.register(curses.KEY_LEFT, 'h')
    def exit_submission(self):
        "Close the submission and return to the subreddit page"

        self.active = False

    @SubmissionController.register(curses.KEY_F5, 'r')
    def refresh_content(self, order=None):
        "Re-download comments and reset the page index"

        order = order or self.content.order
        url = self.content.name

        with self.term.loader:
            self.content = SubmissionContent.from_url(
                self.reddit, url, self.term.loader, order=order)
        if not self.term.loader.exception:
            self.nav = Navigator(self.content.get, page_index=-1)

    @SubmissionController.register(curses.KEY_ENTER, Terminal.RETURN, 'o')
    def open_link(self):
        "Open the selected item with the webbrowser"

        data = self.content.get(self.nav.absolute_index)
        url = data.get('permalink')
        if url:
            self.term.open_browser(url)
        else:
            self.term.flash()

    @SubmissionController.register('c')
    @logged_in
    def add_comment(self):
        """
        Submit a reply to the selected item.

        Selected item:
            Submission - add a top level comment
            Comment - add a comment reply
        """

        data = self.content.get(self.nav.absolute_index)
        if data['type'] == 'Submission':
            body = data['text']
            reply = data['object'].add_comment
        elif data['type'] == 'Comment':
            body = data['body']
            reply = data['object'].reply
        else:
            self.term.flash()
            return

        # Construct the text that will be displayed in the editor file.
        # The post body will be commented out and added for reference
        lines = ['# |' + line for line in body.split('\n')]
        content = '\n'.join(lines)
        comment_info = COMMENT_FILE.format(
            author=data['author'],
            type=data['type'].lower(),
            content=content)

        comment = self.term.open_editor(comment_info)
        if not comment:
            self.term.show_notification('Aborted')
            return

        with self.term.loader(message='Posting', delay=0):
            reply(comment)
            # Give reddit time to process the submission
            time.sleep(2.0)
        if not self.term.loader.exception:
            self.refresh_content()

    @SubmissionController.register('d')
    @logged_in
    def delete_comment(self):
        "Delete a comment as long as it is not the current submission"

        if self.nav.absolute_index != -1:
            self.delete_item()
        else:
            self.term.flash()

    def _draw_item(self, win, data, inverted=False):

        if data['type'] == 'MoreComments':
            return self._draw_more_comments(win, data)
        elif data['type'] == 'HiddenComment':
            return self._draw_more_comments(win, data)
        elif data['type'] == 'Comment':
            return self._draw_comment(win, data, inverted=inverted)
        else:
            return self._draw_submission(win, data)

    def _draw_comment(self, win, data, inverted=False):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1

        # Handle the case where the window is not large enough to fit the text.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        row = offset
        if row in valid_rows:

            attr = curses.A_BOLD
            attr |= (Color.BLUE if not data['is_author'] else Color.GREEN)
            self.term.add_line(win, '{author} '.format(**data), row, 1, attr)

            if data['flair']:
                attr = curses.A_BOLD | Color.YELLOW
                self.term.add_line(win, '{flair} '.format(**data), attr=attr)

            text, attr = self.term.get_arrow(data['likes'])
            self.term.add_line(win, text, attr=attr)
            self.term.add_line(win, ' {score} {created} '.format(**data))

            if data['gold']:
                text, attr = self.term.gold
                self.term.add_line(win, text, attr=attr)

        for row, text in enumerate(data['split_body'], start=offset+1):
            if row in valid_rows:
                self.term.add_line(win, text, row, 1)

        # Unfortunately vline() doesn't support custom color so we have to
        # build it one segment at a time.
        attr = Color.get_level(data['level'])
        x = 0
        for y in range(n_rows):
            self.term.addch(win, y, x, curses.ACS_VLINE, attr)

        return attr | curses.ACS_VLINE

    def _draw_more_comments(self, win, data):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1

        self.term.add_line(win, '{body}'.format(**data), 0, 1)
        self.term.add_line(win, ' [{count}]'.format(**data), attr=curses.A_BOLD)

        attr = Color.get_level(data['level'])
        self.term.addch(win, 0, 0, curses.ACS_VLINE, attr)

        return attr | curses.ACS_VLINE

    def _draw_submission(self, win, data):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 3  # one for each side of the border + one for offset

        for row, text in enumerate(data['split_title'], start=1):
            self.term.add_line(win, text, row, 1, curses.A_BOLD)

        row = len(data['split_title']) + 1
        attr = curses.A_BOLD | Color.GREEN
        self.term.add_line(win, '{author}'.format(**data), row, 1, attr)
        attr = curses.A_BOLD | Color.YELLOW
        if data['flair']:
            self.term.add_line(win, ' {flair}'.format(**data), attr=attr)
        self.term.add_line(win, ' {created} {subreddit}'.format(**data))

        row = len(data['split_title']) + 2
        attr = curses.A_UNDERLINE | Color.BLUE
        self.term.add_line(win, '{url}'.format(**data), row, 1, attr)
        offset = len(data['split_title']) + 3

        # Cut off text if there is not enough room to display the whole post
        split_text = data['split_text']
        if data['n_rows'] > n_rows:
            cutoff = data['n_rows'] - n_rows + 1
            split_text = split_text[:-cutoff]
            split_text.append('(Not enough space to display)')

        for row, text in enumerate(split_text, start=offset):
            self.term.add_line(win, text, row, 1)

        row = len(data['split_title']) + len(split_text) + 3
        self.term.add_line(win, '{score} '.format(**data), row, 1)
        text, attr = self.term.get_arrow(data['likes'])
        self.term.add_line(win, text, attr=attr)
        self.term.add_line(win, ' {comments} '.format(**data))

        if data['gold']:
            text, attr = self.term.gold
            self.term.add_line(win, text, attr=attr)

        if data['nsfw']:
            text, attr = 'NSFW', (curses.A_BOLD | Color.RED)
            self.term.add_line(win, text, attr=attr)

        win.border()
