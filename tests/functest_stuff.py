import os
import sys
import time
import shlex
import signal
import select
import subprocess

import pytest

# py.test -s
# http://stackoverflow.com/questions/2715847/python-read-streaming-input-from-subprocess-communicate

@pytest.yield_fixture()
def rtv():

    cwd = os.path.join(os.path.dirname(__file__), '..')
    rtv = subprocess.Popen([sys.executable, '-m', 'rtv'], stdin=subprocess.PIPE, cwd=cwd)
    yield rtv
    rtv.terminate()

def test_sanity(rtv):

    for i in xrange(5):
        rtv.stdin.write('j')
        time.sleep(0.5)

# http://stackoverflow.com/a/4791612
# cmd = 'x-terminal-emulator -e "rtv --log=/tmp/log.txt"'
# # cmd = 'rtv --log=/tmp/log.txt'
# cmd = shlex.split(cmd)
# rtv = subprocess.Popen(cmd, stdin=subprocess.PIPE)
# time.sleep(5)
# rtv.stdin.write('j')
# time.sleep(5)
# rtv.terminate()

# https://pymotw.com/2/subprocess/index.html#module-subprocess
#
# cmd = ['gnome-terminal', '-x', 'rtv', '--log=/tmp/log.txt']
# rtv = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
#                        preexec_fn=os.setsid, close_fds=False)
# time.sleep(3)
# rtv.stdin.write('?')
# rtv.stdin.flush()
# # while select.select([rtv.stdin,],[],[],0.0)[0]:
# #     print 'waiting'
# # print 'empty!'
# time.sleep(2)
# os.killpg(rtv.pid, signal.SIGTERM)