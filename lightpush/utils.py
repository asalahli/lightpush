import os
import sys


class FatalError(Exception):
    pass


def create_packet(message):
    packet = bytearray(message)
    packet.insert(0, len(packet))
    packet.insert(0, 129)
    return packet


def daemonize(pidfile, logfile):
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

        pid = os.getpid()
        f = open(pidfile, 'w')
        f.write('%s\n' % pid)
        f.close()

        # Change current directory to root
        os.chdir('/')

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open('/dev/null', 'r')
        so = open(logfile, 'a+')
        se = open(logfile, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
    except OSError as e:
        raise FatalError('Failed to start lightpush daemon.')