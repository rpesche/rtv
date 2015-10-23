import sys
import locale
import logging

import praw
import tornado
from praw.errors import PRAWException
from requests.exceptions import RequestException

from .config import Config
from .exceptions import RTVError
from .curses_helpers import curses_session
from .subreddit import SubredditPage
from .docs import AGENT
from .oauth import OAuthTool
from .__version__ import __version__

__all__ = []
_logger = logging.getLogger(__name__)

# Pycharm debugging note:
# You can use pycharm to debug a curses application by launching rtv in a
# console window (python -m rtv) and using pycharm to attach to the remote
# process. On Ubuntu, you may need to allow ptrace permissions by setting
# ptrace_scope to 0 in /etc/sysctl.d/10-ptrace.conf.
# http://blog.mellenthin.de/archives/2010/10/18/gdb-attach-fails


def main():
    "Main entry point"

    # Squelch SSL warnings
    logging.captureWarnings(True)
    locale.setlocale(locale.LC_ALL, '')

    # Set the terminal title
    title = 'rtv {0}'.format(__version__)
    sys.stdout.write("\x1b]2;{0}\x07".format(title))

    # Attempt to load from the config file first, and then overwrite with any
    # provided command line arguments.
    config = Config()
    config.from_file()
    config.from_args()
    config.load_history()

    config.load_refresh_token()
    if config['clear_auth']:
        config.delete_refresh_token()

    if config['log']:
        logging.basicConfig(level=logging.DEBUG, filename=config['log'])
    else:
        # Add a handler so the logger doesn't complain
        logging.root.addHandler(logging.NullHandler())

    try:
        print('Connecting...')
        user_agent = AGENT.format(version=__version__)
        reddit = praw.Reddit(user_agent=user_agent, decode_html_entities=False)
        with curses_session() as stdscr:

            # Authorize on launch if the refresh token is present
            oauth = OAuthTool(stdscr, reddit, config)
            if config.refresh_token:
                oauth.authorize()

            page = SubredditPage(stdscr, reddit, config, oauth,
                                 name=config['subreddit'], url=config['link'])
            page.loop()
    except (RequestException, PRAWException, RTVError) as e:
        _logger.exception(e)
        print('{}: {}'.format(type(e).__name__, e))
    except KeyboardInterrupt:
        pass
    finally:
        config.save_history()
        # Ensure sockets are closed to prevent a ResourceWarning
        if 'reddit' in locals():
            reddit.handler.http.close()
        # Explicitly close file descriptors opened by Tornado's IOLoop
        tornado.ioloop.IOLoop.current().close(all_fds=True)

sys.exit(main())
