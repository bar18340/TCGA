# tcga/main.py

from tcga.interface.gui import GUI
from tcga.utils.logger import setup_logger

def main():
    logger = setup_logger()
    try:
        logger.info("Launching TCGA GUI")
        gui = GUI(logger)  # Pass logger to GUI
        gui.run()
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")  # Ensure visibility in the terminal

if __name__ == '__main__':
    main()
