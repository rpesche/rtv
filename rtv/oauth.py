import time
import uuid

from praw.errors import OAuthAppRequired, OAuthInvalidToken
from tornado import gen, ioloop, web, httpserver
from concurrent.futures import ThreadPoolExecutor

from .terminal import Terminal
from .helpers import open_browser


class OAuthHandler(web.RequestHandler):

    state, code, error = None, None, None

    def get(self):
        self.state = self.get_argument('state', default='')
        self.code = self.get_argument('code', default='')
        self.error = self.get_argument('error', default='')

        self.render('index.html', state=self.state, code=self.code,
                    error=self.error)

        # Stop IOLoop if using a background browser such as firefox
        # if check_browser_display():
        if True:
            ioloop.IOLoop.current().stop()


class OAuthTool(Terminal):

    def __init__(self, stdscr, reddit, config):

        super(OAuthTool, self).__init__(stdscr, config)

        self.reddit = reddit
        self.http_server = None

        # Initialize Tornado webapp
        routes = [('/', OAuthHandler)]
        self.callback_app = web.Application(
            routes, template_path=config['template_path'])

        self.reddit.set_oauth_app_info(
            config['oauth_client_id'],
            config['oauth_client_secret'],
            config['oauth_redirect_uri'])

        # Reddit's mobile website works better on terminal browsers
        if not self.display:
            if '.compact' not in self.reddit.config.API_PATHS['authorize']:
                self.reddit.config.API_PATHS['authorize'] += '.compact'

    def authorize(self):

        # If we already have a token, request new access credentials
        if self.config.refresh_token:
            with self.loader(message='Logging in'):
                self.reddit.refresh_access_information(self.config.refresh_token)
                return

        # Start the authorization callback server
        if self.http_server is None:
            self.http_server = httpserver.HTTPServer(self.callback_app)
            self.http_server.listen(self.config['oauth_redirect_port'])

        hex_uuid = uuid.uuid4().hex
        authorize_url = self.reddit.get_authorize_url(
            unique_id, scope=self.config['oauth_scope'], refreshable=True)

        # Open the browser and wait for the user to authorize the app
        if not self.display:
            with self.loader(message='Waiting for authorization'):
                open_browser(authorize_url)
                ioloop.IOLoop.current().start()
        else:
            with self.loader(delay=0, message='Redirecting to reddit'):
                time.sleep(1)  # User feedback
            ioloop.IOLoop.current().add_callback(self._open_authorize_url,
                                                 authorize_url)
            ioloop.IOLoop.current().start()

        if OAuthHandler.error == 'access_denied':
            self.show_notification('Declined access')
            return
        elif OAuthHandler.error is not None:
            self.show_notification('Authentication error')
            return
        elif hex_uuid != OAuthHandler.state:
            self.show_notification('UUID mismatch')
            return

        try:
            with self.loader(message='Logging in'):
                access_info = self.reddit.get_access_information(OAuthHandler.code)
                self.config.refresh_token = access_info['refresh_token']
                if self.config['persistent']:
                    config.save_refresh_token()
        except (OAuthAppRequired, OAuthInvalidToken):
            self.show_notification('Invalid OAuth data')
        else:
            self.show_notification('Welcome {}!'.format(self.reddit.user.name))

    def clear_oauth_data(self):
        self.reddit.clear_authentication()
        self.config.clear_refresh_token()

    @gen.coroutine
    def _open_authorize_url(self, url):
        with ThreadPoolExecutor(max_workers=1) as executor:
            yield executor.submit(open_browser, url)
        ioloop.IOLoop.current().stop()
