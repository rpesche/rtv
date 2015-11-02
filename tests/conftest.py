import pytest

from rtv.config import Config

try:
    from unittest import mock
except ImportError:
    import mock

@pytest.fixture(scope="module", params=[{'ascii': True}, {'ascii': False}])
def config(request):
    return Config(**request.param)

@pytest.fixture(scope="function")
def stdscr():
    return mock.MagicMock()