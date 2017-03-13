import logging

logger = logging.getLogger(__name__)


_log_formatter = logging.Formatter(
    fmt='%(asctime)s [%(levelname)s %(filename)s:%(lineno)s in %(funcName)s] %(message)s')
_log_handler = logging.FileHandler('/var/log/switchdc.log')
_log_handler.setFormatter(_log_formatter)
logger.addHandler(_log_handler)
logger.raiseExceptions = False
logger.setLevel(logging.INFO)
