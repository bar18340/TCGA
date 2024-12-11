# tcga/utils/logger.py

import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    logger = logging.getLogger('TCGA')
    logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all logs

    # Create a rotating file handler
    handler = RotatingFileHandler('tcga.log', maxBytes=5*1024*1024, backupCount=5)
    handler.setLevel(logging.DEBUG)

    # Create a logging format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Add the handlers to the logger
    if not logger.handlers:
        logger.addHandler(handler)

    return logger
