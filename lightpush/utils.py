import os
import sys

from lightpush.exceptions import FatalError


def daemonize():
    """Daemonizes current process

    This function executes the steps specified in 
    Advanced Programming in the UNIX Environment, 3rd Edition
    """
    try:
        # Clear file creation mask
        os.umask(0)

        # First fork()
        pid = os.fork()
        if pid > 0:
            sys.exit(0)

        # Create a new session
        os.setsid()
        pid = os.fork()
        if pid > 0:
            sys.exit(0)

        # Change current directory to root
        os.chdir('/')

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file('/dev/null', 'r')
        so = file('/dev/null', 'a+')
        se = file('/dev/null', 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
    except OSError, e:
        raise FatalError('Failed to start the server: %s' %e)

