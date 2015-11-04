# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import uuid

from praw.errors import OAuthAppRequired, OAuthException
from tornado import gen, ioloop, web, httpserver
from concurrent.futures import ThreadPoolExecutor

from .helpers import open_browser


class OAuthHandler(web.RequestHandler):
    """
    Intercepts the redirect that Reddit sends the user to after they verify or
    deny the application access.

    The GET should supply 3 request params:
        state: Unique id that was supplied by us at the beginning of the
               process to verify that the session matches.
        code: Code that we can use to generate the refresh token.
        error: If an error occurred, it will be placed here.
    """

    display = None
    state, code, error = None, None, None

    def get(self):
        self.state = self.get_argument('state', default='')
        self.code = self.get_argument('code', default='')
        self.error = self.get_argument('error', default='')

        self.render('index.html', state=self.state, code=self.code,
                    error=self.error)

        # Stop IOLoop if using a background browser such as firefox
        if self.display:
            ioloop.IOLoop.current().stop()


class OAuthHelper(object):

    def __init__(self, reddit, term, config):

        self.term = term
        self.reddit = reddit
        self.config = config

        self.http_server = None

        # Initialize Tornado webapp
        OAuthHandler.display = self.term.display
        routes = [('/', OAuthHandler)]
        self.callback_app = web.Application(
            routes, template_path=self.config['template_path'])

        self.reddit.set_oauth_app_info(
            self.config['oauth_client_id'],
            self.config['oauth_client_secret'],
            self.config['oauth_redirect_uri'])

        # Reddit's mobile website works better on terminal browsers
        if not self.term.display:
            if '.compact' not in self.reddit.config.API_PATHS['authorize']:
                self.reddit.config.API_PATHS['authorize'] += '.compact'

    def authorize(self):

        # If we already have a token, request new access credentials
        if self.config.refresh_token:
            with self.term.loader(message='Logging in'):
                self.reddit.refresh_access_information(
                    self.config.refresh_token)
                return

        # Start the authorization callback server
        if self.http_server is None:
            self.http_server = httpserver.HTTPServer(self.callback_app)
            self.http_server.listen(self.config['oauth_redirect_port'])

        state = uuid.uuid4().hex
        authorize_url = self.reddit.get_authorize_url(
            state, scope=self.config['oauth_scope'], refreshable=True)

        # Open the browser and wait for the user to authorize the app
        if self.term.display:
            with self.term.loader(message='Waiting for authorization'):
                open_browser(authorize_url, self.term.display)
                ioloop.IOLoop.current().start()
        else:
            with self.term.loader(delay=0, message='Redirecting to reddit'):
                time.sleep(1)  # User feedback
            ioloop.IOLoop.current().add_callback(self._open_authorize_url,
                                                 authorize_url)
            ioloop.IOLoop.current().start()

        if OAuthHandler.error == 'access_denied':
            self.term.show_notification('Declined access')
            return
        elif OAuthHandler.error is not None:
            self.term.show_notification('Authentication error')
            return
        elif state != OAuthHandler.state:
            self.term.show_notification('UUID mismatch')
            return

        try:
            with self.term.loader(message='Logging in'):
                info = self.reddit.get_access_information(OAuthHandler.code)
                self.config.refresh_token = info['refresh_token']
                if self.config['persistent']:
                    self.config.save_refresh_token()
        except (OAuthAppRequired, OAuthException):
            self.term.show_notification('Invalid OAuth data')
        else:
            message = 'Welcome {}!'.format(self.reddit.user.name)
            self.term.show_notification(message)

    def clear_oauth_data(self):
        self.reddit.clear_authentication()
        self.config.clear_refresh_token()

    @gen.coroutine
    def _open_authorize_url(self, url):
        with ThreadPoolExecutor(max_workers=1) as executor:
            yield executor.submit(open_browser, url, self.term.display)
        ioloop.IOLoop.current().stop()
