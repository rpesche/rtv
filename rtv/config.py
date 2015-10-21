"""
Global configuration settings
"""
import os
import codecs
import argparse
from six.moves import configparser

from . import docs, __version__

HOME = os.path.expanduser('~')
XDG_HOME = os.getenv('XDG_CONFIG_HOME', os.path.join(HOME, '.config'))
CONFIG = os.path.join(XDG_HOME, 'rtv', 'rtv.cfg')
TOKEN = os.path.join(XDG_HOME, 'rtv', 'refresh-token')
HISTORY = os.path.join(XDG_HOME, 'rtv', 'history.log')

def build_parser():
    parser = argparse.ArgumentParser(
        prog='rtv', description=docs.SUMMARY,
        epilog=docs.CONTROLS+docs.HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '-V', '--version', action='version', version='rtv '+__version__,
    )
    parser.add_argument(
        '-s', dest='subreddit',
        help='name of the subreddit that will be opened on start')
    parser.add_argument(
        '-l', dest='link',
        help='full URL of a submission that will be opened on start')
    parser.add_argument(
        '--ascii', action='store_true',
        help='enable ascii-only mode')
    parser.add_argument(
        '--log', metavar='FILE', action='store',
        help='log HTTP requests to a file')
    parser.add_argument(
        '--non-persistent', dest='persistent', action='store_false',
        help='Forget all authenticated users when the program exits')
    parser.add_argument(
        '--clear-auth', dest='clear_auth', action='store_true',
        help='Remove any saved OAuth tokens before starting')
    return parser

class OrderedSet(object):
    """
    A simple implementation of an ordered set. A set is used to check
    for membership, and a list is used to maintain ordering.
    """

    def __init__(self, elements=[]):
        self._set = set(elements)
        self._list = elements

    def __contains__(self, item):
        return item in self._set

    def __len__(self):
        return len(self._list)

    def __getitem__(self, item):
        return self._list[item]

    def add(self, item):
        self._set.add(item)
        self._list.append(item)

class Config(dict):

    def __init__(self, **kwargs):

        self.oauth_token = None
        self.history = OrderedSet()
        self.update({
            'config_filename': CONFIG,
            'history_filename': HISTORY,
            'token_filename': TOKEN,
            'ascii': False,
            'persistent': True,
            'clear_auth': False,
            # https://github.com/reddit/reddit/wiki/OAuth2
            # Client ID is of type "installed app" and the secret should be empty
            'oauth_client_id': 'E2oEtRQfdfAfNQ',
            'oauth_client_secret': 'praw_gapfill',
            'oauth_redirect_uri': 'http://127.0.0.1:65000/',
            'oauth_redirect_port': 65000,
            'oauth_scope': ['edit', 'history', 'identity', 'mysubreddits',
                            'privatemessages', 'read', 'report', 'save',
                            'submit', 'subscribe', 'vote']
        })

        self.update(kwargs)

    def load_args(self):

        parser = build_parser()
        args = parser.parse_args()
        self.update(args)

    def load_config(self, filename=None):

        filename = filename or self['config_filename']
        config = configparser.ConfigParser()
        if os.path.exists(filename):
            config.read(filename)

        config_dict = {}
        if config.has_section('rtv'):
            config_dict = dict(config.items('rtv'))

        # Convert 'true'/'false' to boolean True/False
        if 'ascii' in config_dict:
            config_dict['ascii'] = config.getboolean('rtv', 'ascii')
        if 'clear_auth' in config_dict:
            config_dict['clear_auth'] = config.getboolean('rtv', 'clear_auth')
        if 'persistent' in config_dict:
            config_dict['persistent'] = config.getboolean('rtv', 'persistent')

        self.update(config_dict)

    def load_refresh_token(self, filename=None):

        filename = filename or self['token_filename']
        if os.path.exists(filename):
            with open(filename) as fp:
                return fp.read().strip()
        return None

    def write_refresh_token(self, filename=None):

        filename = filename or self['token_filename']
        filepath = os.path.basename(filename)
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        with open(filename, 'w+') as fp:
            fp.write(self['oauth_token'])

    def delete_refresh_token(self, filename=None):

        filename = filename or self['refresh_filename']
        if os.path.exists(filename):
            os.remove(filename)

    def load_history(self, filename=None):

        filename = filename or self['history_filename']
        if os.path.exists(filename):
            with codecs.open(filename, encoding='utf-8') as fp:
                return OrderedSet([line.strip() for line in fp])
        return OrderedSet()

    def write_history(self, filename=None):

        filename = filename or self['history_filename']
        filepath = os.path.basename(filename)
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        with codecs.open(filename, 'w+', encoding='utf-8') as fp:
            fp.writelines(self.history[-200:])