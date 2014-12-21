import ConfigParser
import getopt
import sys

from lightpush.exceptions import FatalError
from lightpush.info import *
from lightpush.utils import daemonize


def start(config):
    daemonize()
    while 1:
        pass


def print_usage():
    print 'usage: %s <command> config-file' % project_name
    print ''
    print '%s' % project_description
    print ''
    print 'Commands:               '
    print '    start               starts the server'
    print '    restart             restarts the server'
    print '    stop                stops the server'
    print ''
    print 'Options:'
    print '    config-file         path to a configuration file'
    print ''


def parse_args():
    """Command line argument parser"""
    try:
        assert len(sys.argv) == 3
        assert COMMANDS.has_key(sys.argv[1]) == True
    except AssertionError:
        print_usage()
        raise FatalError('Invalid arguments.')

    command = sys.argv[1]
    config_file = sys.argv[2]
    return command, config_file


def load_config(config_file):
    config = ConfigParser.ConfigParser()
    try:
        assert len(config.read(config_file)) == 1
    except AssertionError:
        raise FatalError('Configuration file could not be read.')
    except ConfigParser.Error:
        raise FatalError('Invalid configuration file.')

    return config


COMMANDS = {
    'start': start,
    'restart': None,
    'stop': None
}


def main():
    """Entry point for `lightpush` command"""
    try:
        command, config_file = parse_args()
        config = load_config(config_file)
        cmd = COMMANDS[command]
        cmd(config)
    except FatalError, e:
        print "Error: %s" % e
        sys.exit()
