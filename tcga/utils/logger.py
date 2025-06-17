# tcga/utils/logger.py

import logging
import os

def setup_logger(log_file='tcga.log', level=logging.DEBUG):
    """
    Sets up the logger for the application.

    Parameters:
        log_file (str): Path to the log file.
        level (int): Logging level.

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger('TCGA_Logger')
    logger.setLevel(level)

    # Create handlers if they haven't been created yet
    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)  # Only log errors to console

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger
