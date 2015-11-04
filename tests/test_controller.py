# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rtv.page import Controller

try:
    from unittest import mock
except ImportError:
    import mock


def test_controller():

    class ControllerA(Controller):
        character_map = {}

    class ControllerB(ControllerA):
        character_map = {}

    class ControllerC(ControllerA):
        character_map = {}

    @ControllerA.register('1')
    def call_page(page):
        return 'a1'

    @ControllerA.register('2')
    def call_page(page):
        return 'a2'

    @ControllerB.register('1')
    def call_page(page):
        return 'b1'

    @ControllerC.register('2')
    def call_page(page):
        return 'c2'

    page = mock.MagicMock()
    controller_a = ControllerA(page)
    controller_b = ControllerB(page)
    controller_c = ControllerC(page)

    assert controller_a.trigger('1') == 'a1'
    assert controller_a.trigger('2') == 'a2'
    assert controller_a.trigger('3') is None

    assert controller_b.trigger('1') == 'b1'
    assert controller_b.trigger('2') == 'a2'
    assert controller_b.trigger('3') is None

    assert controller_c.trigger('1') == 'a1'
    assert controller_c.trigger('2') == 'c2'
    assert controller_c.trigger('3') is None