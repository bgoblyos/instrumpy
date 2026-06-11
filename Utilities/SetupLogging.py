import logging

def setupLogging():
    logging.basicConfig(
        level = logging.INFO,
        format = '%(levelname)s\t- %(name)s - %(message)s',
        force = True
    )
    return logging.getLogger('instrumpy')