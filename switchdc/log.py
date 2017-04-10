from __future__ import print_function

import logging
import os
import pwd
import socket
import sys

from switchdc.dry_run import is_dry_run


logger = logging.getLogger(__name__)
irc_logger = logging.getLogger(__name__ + '_irc_announce')


class IRCSocketHandler(logging.Handler):
    """Log handler for logmsgbot on #wikimedia-operation.

    Sends log events to a tcpircbot server for relay to an IRC channel.
    """

    def __init__(self, host, port):
        """Initialize the IRC socket handler.

        Arguments:
        host -- tcpircbot host
        port -- tcpircbot listening port
        """
        super(IRCSocketHandler, self).__init__()
        self.addr = (host, port)
        self.level = logging.INFO
        try:
            self.user = os.getlogin()
        except OSError:
            self.user = pwd.getpwuid(os.getuid())[0]

    def emit(self, record):
        """According to Python logging.Handler interface.

        See https://docs.python.org/2/library/logging.html#handler-objects
        """
        message = '!log switchdc ({user}@{host}) {msg}'.format(
            user=self.user, host=socket.gethostname(), msg=record.getMessage())
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(self.addr)
            sock.sendall(message)
        except (socket.timeout, socket.error, socket.gaierror):
            self.handleError(record)
        finally:
            if sock is not None:
                sock.close()


class OutputHandler(logging.StreamHandler):
    """A StreamHandler to stderr that handles DRY-RUN mode."""

    def emit(self, record):
        """According to Python logging.Handler interface.

        See https://docs.python.org/2/library/logging.html#handler-objects
        """
        if is_dry_run():
            record = 'DRY-RUN: {message}'.format(message=record)

        super(OutputHandler, self).emit(record)


def setup_irc(config):
    """Setup the IRC logger instance."""
    # Only one handler should be present
    if irc_logger.handlers:
        return
    irc_logger.addHandler(IRCSocketHandler(config['tcpircbot_host'], config['tcpircbot_port']))
    irc_logger.setLevel(logging.INFO)


def setup_logging():
    """Setup the logger instance."""
    # Default INFO logging
    formatter = logging.Formatter(fmt='%(asctime)s [%(levelname)s] %(message)s')
    handler = logging.FileHandler('/var/log/switchdc.log')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    # Extended logging for detailed debugging
    formatter_extended = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s %(filename)s:%(lineno)s in %(funcName)s] %(message)s')
    handler_extended = logging.FileHandler('/var/log/switchdc-extended.log')
    handler_extended.setFormatter(formatter_extended)
    handler_extended.setLevel(logging.DEBUG)

    # Stderr logging
    output_handler = OutputHandler()
    if is_dry_run():
        output_handler.setLevel(logging.DEBUG)
    else:
        output_handler.setLevel(logging.INFO)

    logger.addHandler(handler)
    logger.addHandler(handler_extended)
    logger.addHandler(output_handler)
    logger.raiseExceptions = False


def stderr(message):
    """Print a message to stderr."""
    print(message, file=sys.stderr)


def log_dry_run(message):
    """Print a DRY-RUN message using stderr."""
    stderr('DRY-RUN: {message}'.format(message=message))


def log_task_start(prefix, message):
    """Log the start of a task."""
    _log_task('START', prefix, message)


def log_task_end(prefix, message):
    """Log the end of a task."""
    _log_task('END', prefix, message)


def _log_task(action, prefix, message):
    message = '{action} TASK - {prefix} {message}'.format(action=action, prefix=prefix, message=message)

    logger.info(message)
    if not is_dry_run():
        irc_logger.info(message)
