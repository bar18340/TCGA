# tcga/controller/controller.py

from tcga.data.file_handler import FileHandler
from tcga.utils.logger import setup_logger

class Controller:
    def __init__(self, logger=None):
        """
        Initializes the Controller with a FileHandler instance.

        Parameters:
            logger (logging.Logger, optional): Custom logger. Defaults to None.
        """
        self.logger = logger if logger else setup_logger()
        self.file_handler = FileHandler(logger=self.logger)

    def process_files(self, methylation_path, gene_mapping_path, zero_percent):
        """
        Handles the process of uploading and merging files.

        Parameters:
            methylation_path (str): Path to the methylation TSV file.
            gene_mapping_path (str): Path to the gene mapping TSV file.
            zero_percent (float): Maximum allowable percentage of zeros.

        Returns:
            tuple: (cleaned DataFrame, number of rows removed)
        """
        try:
            # Upload files
            methylation_file_name = self.file_handler.upload_file(methylation_path, 'methylation')
            gene_mapping_file_name = self.file_handler.upload_file(gene_mapping_path, 'gene_mapping')

            # Merge and clean files
            merged_df, rows_removed = self.file_handler.merge_files(zero_percent=zero_percent)

            return merged_df, rows_removed

        except Exception as e:
            self.logger.error(f"Error processing files: {e}")
            raise e
