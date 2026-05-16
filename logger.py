import logging
import sys


def get_logger(name, debug=False):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if debug:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)
    return logger
