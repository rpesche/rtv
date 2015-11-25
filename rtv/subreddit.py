# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import curses

import six
import requests

from .exceptions import SubredditError, AccountError
from .page import Page, PageController, logged_in
from .objects import Navigator
from .submission import SubmissionPage
from .subscription import SubscriptionPage
from .content import SubredditContent
from .terminal import Terminal
from .docs import SUBMISSION_FILE


class SubredditController(PageController):
    character_map = {}


class SubredditPage(Page):

    def __init__(self, stdscr, reddit, config, oauth, name, url=None):
        """
        Params:
            name (string): Name of subreddit to open
            url (string): Optional submission to load upon start
        """

        super(SubredditPage, self).__init__(stdscr, reddit, config, oauth)

        self.content = SubredditContent.from_name(reddit, name, self.loader)
        self.controller = SubredditController(self)
        self.nav = Navigator(self.content.get)

        if url:
            self.open_submission(url=url)

    @SubredditController.register(curses.KEY_F5, 'r')
    def refresh_content(self, name=None, order=None):
        "Re-download all submissions and reset the page index"

        name = name or self.content.name
        order = order or self.content.order

        # Hack to allow an order specified in the name by prompt_subreddit() to
        # override the current default
        if order == 'ignore':
            order = None

        try:
            self.content = SubredditContent.from_name(
                self.reddit, name, self.loader, order=order)
        except AccountError:
            self.show_notification('Not logged in')
        except SubredditError:
            self.show_notification('Invalid subreddit')
        except requests.HTTPError:
            self.show_notification('Could not reach subreddit')
        else:
            self.nav = Navigator(self.content.get)

    @SubredditController.register('f')
    def search_subreddit(self, name=None):
        "Open a prompt to search the given subreddit"

        name = name or self.content.name

        query = self.prompt_input('Search {}:'.format(name))
        if query is None:
            return

        try:
            self.content = SubredditContent.from_name(
                self.reddit, name, self.loader, query=query)
        except (IndexError, SubredditError):
            self.show_notification('No results found')
        else:
            self.nav = Navigator(self.content.get)

    @SubredditController.register('/')
    def prompt_subreddit(self):
        "Open a prompt to navigate to a different subreddit"

        name = self.prompt_input('Enter Subreddit: /r/')
        if name is not None:
            self.refresh_content(name=name, order='ignore')

    @SubredditController.register(curses.KEY_RIGHT, 'l')
    def open_submission(self, url=None):
        "Select the current submission to view posts"

        if url is None:
            data = self.content.get(self.nav.absolute_index)
            url, url_type = data['url_full'], data['url_type']
        else:
            url_type = None

        page = SubmissionPage(
            self.stdscr, self.reddit, self.config, self.oauth, url=url)
        page.loop()

        if url_type == 'selfpost':
            self.config.history.add(url)

    @SubredditController.register(curses.KEY_ENTER, Terminal.RETURN, 'o')
    def open_link(self):
        "Open a link with the webbrowser"

        data = self.content.get(self.nav.absolute_index)
        url = data['url_full']

        if data['url_type'] in ['x-post', 'selfpost']:
            page = SubmissionPage(
                self.stdscr, self.reddit, self.config, self.oauth, url=url)
            page.loop()
        else:
            open_browser(url)

        self.config.history.add(url)

    @SubredditController.register('c')
    @logged_in
    def post_submission(self):
        "Post a new submission to the given subreddit"

        # Strips the subreddit to just the name
        # Make sure it is a valid subreddit for submission
        subreddit = self.reddit.get_subreddit(self.content.name)
        sub = six.text_type(subreddit).split('/')[2]
        if '+' in sub or sub in ('all', 'front', 'me'):
            self.show_notification('Invalid subreddit')
            return

        submission_info = SUBMISSION_FILE.format(name=subreddit, content='')

        submission_text = self.term.open_editor(submission_info)
        if not submission_text:
            self.show_notification('Aborted')
            return
        elif '\n' not in submission_text:
            self.show_notification('No content')
            return
        else:
            title, content = submission_text.split('\n', 1)

        with self.loader(message='Posting', delay=0):
            post = self.reddit.submit(sub, title, text=content)
            time.sleep(2.0)

        if self.loader.exception is None:
            # Open the newly created post
            page = SubmissionPage(self.stdscr, self.reddit, self.config,
                                  self.oauth, submission=post)
            page.loop()
            self.refresh_content()

    @SubredditController.register('s')
    @logged_in
    def open_subscriptions(self):
        "Open user subscriptions page"

        page = SubscriptionPage(
            self.stdscr, self.reddit, self.config, self.oauth)
        page.loop()

        # When the user has chosen a subreddit in the subscriptions list,
        # refresh content with the selected subreddit
        if page.subreddit_data is not None:
            self.refresh_content(name=page.subreddit_data['name'])

    def draw_item(self, win, data, inverted=False):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        n_title = len(data['split_title'])
        for row, text in enumerate(data['split_title'], start=offset):
            if row in valid_rows:
                self.add_line(win, text, row, 1, curses.A_BOLD)

        row = n_title + offset
        if row in valid_rows:
            seen = (data['url_full'] in self.config.history)
            link_color = Color.MAGENTA if seen else Color.BLUE
            attr = curses.A_UNDERLINE | link_color
            self.add_line(win, u'{url}'.format(**data), row, 1, attr)

        row = n_title + offset + 1
        if row in valid_rows:
            self.add_line(win, u'{score} '.format(**data), row, 1)
            text, attr = self.get_arrow(data['likes'])
            self.add_line(win, text, attr=attr)
            self.add_line(win, u' {created} {comments} '.format(**data))

            if data['gold']:
                text, attr = self.get_gold()
                self.add_line(win, text, attr=attr)

            if data['nsfw']:
                text, attr = 'NSFW', (curses.A_BOLD | Color.RED)
                self.add_line(win, text, attr=attr)

        row = n_title + offset + 2
        if row in valid_rows:
            self.add_line(
                win, u'{author}'.format(**data), row, 1, curses.A_BOLD)
            self.add_line(
                win, u' /r/{subreddit}'.format(**data), attr=Color.YELLOW)
            if data['flair']:
                self.add_line(win, u' {flair}'.format(**data), attr=Color.RED)