import logging
import coloredlogs

grey = '\x1b[38;21m'
blue = '\x1b[38;5;39m'
yellow = '\x1b[38;5;226m'
red = '\x1b[38;5;196m'
bold_red = '\x1b[31;1m'
reset = '\x1b[0m'

def setup_custom_logger(name):
    # formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    # handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    # logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    coloredlogs.install(level=name, logger=logger, fmt='%(levelname)s %(message)s')
    return logger