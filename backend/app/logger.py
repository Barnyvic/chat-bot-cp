import logging
from pythonjsonlogger import jsonlogger


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("meridian-chatbot")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
