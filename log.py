import logging
import coloredlogs

def setup_custom_logger(name, loglevel):
    handler = logging.StreamHandler()
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    custom_level_styles = {
        "critical": {"bold": True, "color": "red"},
        "debug": {"color": "green"},
        "error": {"color": (234,86,82), "bold": True},
        "info": {},
        "notice": {"color": "magenta"},
        "spam": {"color": "green", "faint": True},
        "success": {"bold": True, "color": "green"},
        "verbose": {"color": "blue"},
        "warning": {"color": (235,204,52)},
    }
    coloredlogs.install(
        level=loglevel,
        logger=logger,
        fmt="%(levelname)s %(message)s",
        level_styles=custom_level_styles
    )
    coloredlogs.ColoredFormatter
    return logger
