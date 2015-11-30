# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import curses

import six

from . import docs
from .content import SubredditContent
from .page import Page, PageController, logged_in
from .objects import Navigator, Color
from .submission import SubmissionPage
from .subscription import SubscriptionPage
from .terminal import Terminal


class SubredditController(PageController):
    character_map = {}


class SubredditPage(Page):

    def __init__(self, reddit, term, config, oauth, name, url=None):
        """
        Params:
            name (string): Name of subreddit to open
            url (string): Optional submission to load upon start
        """
        super(SubredditPage, self).__init__(reddit, term, config, oauth)

        self.content = SubredditContent.from_name(reddit, name, term.loader)
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

        with self.term.loader():
            self.content = SubredditContent.from_name(
                self.reddit, name, self.term.loader, order=order)
        if not self.term.loader.exception:
            self.nav = Navigator(self.content.get)

    @SubredditController.register('f')
    def search_subreddit(self, name=None):
        "Open a prompt to search the given subreddit"

        name = name or self.content.name

        query = self.term.prompt_input('Search {0}:'.format(name))
        if query is None:
            return

        with self.term.loader():
            self.content = SubredditContent.from_name(
                self.reddit, name, self.term.loader, query=query)
        if not self.term.loader.exception:
            self.nav = Navigator(self.content.get)

    @SubredditController.register('/')
    def prompt_subreddit(self):
        "Open a prompt to navigate to a different subreddit"

        name = self.term.prompt_input('Enter Subreddit: /r/')
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

        with self.term.loader():
            page = SubmissionPage(
                self.reddit, self.term, self.config, self.oauth, url=url)
        if self.term.loader.exception:
            return

        page.loop()

        if url_type == 'selfpost':
            self.config.history.add(url)

    @SubredditController.register(curses.KEY_ENTER, Terminal.RETURN, 'o')
    def open_link(self):
        "Open a link with the webbrowser"

        data = self.content.get(self.nav.absolute_index)
        url = data['url_full']

        if data['url_type'] not in ('x-post', 'selfpost'):
            self.term.open_browser(url)
        else:
            with self.term.loader():
                page = SubmissionPage(
                    self.reddit, self.term, self.config, self.oauth, url=url)
            if self.term.loader.exception:
                return

            page.loop()

        self.config.history.add(url)

    @SubredditController.register('c')
    @logged_in
    def post_submission(self):
        "Post a new submission to the given subreddit"

        # Check that the subreddit can be submitted to
        subreddit = self.reddit.get_subreddit(self.content.name)
        sub_name = six.text_type(subreddit).split('/')[2]
        if '+' in sub_name or sub_name in ('all', 'front', 'me'):
            self.term.show_notification('Invalid subreddit')
            return

        submission_info = docs.SUBMISSION_FILE.format(
            name=subreddit, content='')
        text = self.term.open_editor(submission_info)
        if not text or '\n' not in text:
            self.term.show_notification('Aborted')
            return

        title, content = text.split('\n', 1)
        with self.term.loader(message='Posting', delay=0):
            post = self.reddit.submit(sub_name, title, text=content)
            # Give reddit time to process the submission
            time.sleep(2.0)
        if self.term.loader.exception:
            return

        # Open the newly created post
        with self.term.loader():
            page = SubmissionPage(
                self.reddit, self.term, self.config, self.oauth,
                submission=post)
        if self.term.loader.exception:
            return

        page.loop()

        self.refresh_content()

    @SubredditController.register('s')
    @logged_in
    def open_subscriptions(self):
        "Open user subscriptions page"

        with self.term.loader():
            page = SubscriptionPage(
                self.reddit, self.term, self.config, self.oauth)
        if self.term.loader.exception:
            return

        page.loop()

        # When the user has chosen a subreddit in the subscriptions list,
        # refresh content with the selected subreddit
        if page.subreddit_data is not None:
            self.refresh_content(name=page.subreddit_data['name'])

    def _draw_item(self, win, data, inverted=False):

        n_rows, n_cols = win.getmaxyx()
        n_cols -= 1  # Leave space for the cursor in the first column

        # Handle the case where the window is not large enough to fit the data.
        valid_rows = range(0, n_rows)
        offset = 0 if not inverted else -(data['n_rows'] - n_rows)

        n_title = len(data['split_title'])
        for row, text in enumerate(data['split_title'], start=offset):
            if row in valid_rows:
                self.term.add_line(win, text, row, 1, curses.A_BOLD)

        row = n_title + offset
        if row in valid_rows:
            seen = (data['url_full'] in self.config.history)
            link_color = Color.MAGENTA if seen else Color.BLUE
            attr = curses.A_UNDERLINE | link_color
            self.term.add_line(win, '{url}'.format(**data), row, 1, attr)

        row = n_title + offset + 1
        if row in valid_rows:
            self.term.add_line(win, '{score} '.format(**data), row, 1)
            text, attr = self.term.get_arrow(data['likes'])
            self.term.add_line(win, text, attr=attr)
            self.term.add_line(win, ' {created} {comments} '.format(**data))

            if data['gold']:
                text, attr = self.term.gold
                self.term.add_line(win, text, attr=attr)

            if data['nsfw']:
                text, attr = 'NSFW', (curses.A_BOLD | Color.RED)
                self.term.add_line(win, text, attr=attr)

        row = n_title + offset + 2
        if row in valid_rows:
            text = '{author}'.format(**data)
            self.term.add_line(win, text, row, 1, curses.A_BOLD)
            text = ' /r/{subreddit}'.format(**data)
            self.term.add_line(win, text, attr=Color.YELLOW)
            if data['flair']:
                text = ' {flair}'.format(**data)
                self.term.add_line(win, text, attr=Color.RED)