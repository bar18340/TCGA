# tcga/main.py

from tcga.interface.gui import GUI
from tcga.utils.logger import setup_logger

def main():
    logger = setup_logger()
    gui = GUI(logger)
    gui.run()

if __name__ == "__main__":
    main()
