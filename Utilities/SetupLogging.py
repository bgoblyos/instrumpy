import logging
import sys

def setupLogging():
    # 1. Grab your master logger
    logger = logging.getLogger('instrumpy')
    logger.setLevel(logging.INFO)

    # Prevent submodules from messing with the logger
    logger.propagate = False

    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Attach a dedicated StreamHandler
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(levelname)s\t- %(name)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger

def fixLogger():
    for logger_name in logging.root.manager.loggerDict:
        if logger_name.startswith('instrumpy'):
            logging.getLogger(logger_name).disabled = False
