from __future__ import print_function

import logging
import os
import pwd
import socket

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


def setup_irc(config):
    """Setup the IRC logger instance."""
    # Only one handler should be present
    if irc_logger.handlers:
        return
    irc_logger.addHandler(IRCSocketHandler(config['tcpircbot_host'], config['tcpircbot_port']))
    irc_logger.setLevel(logging.INFO)


class OutputFilter(logging.Filter):
    threshold = logging.ERROR

    def filter(self, record):
        if 'cumin' in record.pathname and record.levelno <= self.threshold:
            return 0
        else:
            return 1


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
    output_handler = logging.StreamHandler()
    if is_dry_run():
        output_handler.setFormatter(logging.Formatter(fmt='DRY-RUN: %(message)s'))
        output_handler.setLevel(logging.DEBUG)
        OutputFilter.threshold = logging.WARN
    else:
        output_handler.setLevel(logging.INFO)
    output_handler.addFilter(OutputFilter())

    logger.addHandler(handler)
    logger.addHandler(handler_extended)
    logger.addHandler(output_handler)
    logger.raiseExceptions = False
    logger.setLevel(logging.DEBUG)


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
