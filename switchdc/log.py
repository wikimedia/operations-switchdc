import logging
import os
import pwd
import socket

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


def setup_logging():
    """Setup the logger instance."""
    _log_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s %(filename)s:%(lineno)s in %(funcName)s] %(message)s')
    _log_handler = logging.FileHandler('/var/log/switchdc.log')
    _log_handler.setFormatter(_log_formatter)
    logger.addHandler(_log_handler)
    logger.raiseExceptions = False
    logger.setLevel(logging.INFO)
