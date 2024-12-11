# tcga/utils/logger.py

import logging

def setup_logger():
    logger = logging.getLogger('TCGA')
    logger.setLevel(logging.DEBUG)
    
    # Prevent adding multiple handlers if logger already has handlers
    if not logger.handlers:
        # Create console handler for INFO level
        c_handler = logging.StreamHandler()
        c_handler.setLevel(logging.INFO)
        
        # Create file handler for DEBUG level
        f_handler = logging.FileHandler('tcga.log')
        f_handler.setLevel(logging.DEBUG)
        
        # Create formatter and add it to handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        c_handler.setFormatter(formatter)
        f_handler.setFormatter(formatter)
        
        # Add handlers to the logger
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)
    
    return logger
