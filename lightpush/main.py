import configparser
import logging
import os
import signal
import sys

from lightpush.server import Server
from lightpush.utils import daemonize, FatalError


def print_usage():
    print('usage: lightpush command <config-file>'              )
    print(''                                                    )
    print('A lightweight push notification server for websites.')
    print(''                                                    )
    print('Commands:'                                           )
    print('    start               starts the server'           )
    # print('    restart             restarts the server'       )
    print('    stop                stops the server'            )
    print(''                                                    )
    print('Arguments:'                                          )
    print('    config-file         path to a configuration file')
    print(''                                                    )


def start(config):
    settings = config['General']
    host = settings['host']
    port = int(settings['port'])
    pidfile = settings['pidfile']
    logfile = settings['logfile']
    logging.basicConfig(filename=logfile, level=logging.DEBUG)

    daemonize(pidfile, logfile)
    Server(host, port).main()


def stop(config):
    settings = config['General']
    pidfile = settings['pidfile']
    f = open(pidfile, 'r')
    pid = int(f.readline().strip())
    os.kill(pid, signal.SIGTERM)
    os.remove(pidfile)


def main():
    try:
        if len(sys.argv) != 3:
            print_usage()
            raise FatalError('Invalid arguments.')

        command = sys.argv[1]
        config_file = sys.argv[2]
        config = configparser.ConfigParser()

        try:
            assert len(config.read(config_file)) == 1
        except AssertionError:
            raise FatalError('Configuration file could not be read.')
        except configparser.Error:
            raise FatalError('Invalid configuration file.')

        if command == "start":
            start(config)
        elif command == "stop":
            stop(config)
        else:
            print_usage()
            raise FatalError('Invalid command: %s' % command)
    except FatalError as e:
        print('Error: %s' % e)
