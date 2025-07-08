import os
import polars as pl
from tcga.utils.logger import setup_logger
from tcga.data.data_merger import DataMerger
from tcga.data.data_cleaner import DataCleaner

class FileHandler:
    """
    Handles the uploading, validation, cleaning, and merging of TCGA data files.

    This class manages the lifecycle of methylation, gene mapping, gene expression, and phenotype files.
    It provides methods to upload and validate files, clean and merge data, and perform resource cleanup.
    """

    def __init__(self, logger=None):
        """
        Initializes the FileHandler instance.
        """
        self.logger = logger if logger else setup_logger()

    def load_dataframe(self, file_path: str, file_type: str) -> pl.DataFrame:
        """
        Loads a file into a Polars DataFrame and performs initial validation.
        """
        if not file_path or not os.path.exists(file_path):
            self.logger.warning(f"File path for {file_type} is missing or invalid.")
            return None

        file_name = os.path.basename(file_path)
        self.logger.info(f"Loading {file_type} file: {file_name}")

        try:
            df = pl.read_csv(file_path, separator='\t', infer_schema_length=10000, ignore_errors=True, null_values=["NA", "na", "null", ""])
        except Exception as e:
            error_message = f"Error reading file '{file_name}': {e}"
            self.logger.error(error_message)
            # Re-raise as a ValueError to be caught by the controller.
            raise ValueError(error_message) from e

        if file_type == 'methylation':
            df = df.rename({df.columns[0]: 'Gene_Code'})

        elif file_type == 'gene_mapping':
            if df.shape[1] < 2:
                    raise ValueError("Gene mapping file must have at least two columns.")  
            df = df.select([df.columns[0], df.columns[1]]).rename({
                df.columns[0]: 'Gene_Code',
                df.columns[1]: 'Actual_Gene_Name'
            })
            if df['Gene_Code'].is_duplicated().any():
                self.logger.warning("Duplicate Gene_Code entries found in gene mapping file.")

        elif file_type == 'gene_expression':
            df = df.rename({df.columns[0]: 'Gene_Name'})
            if df['Gene_Name'].is_duplicated().any():
                self.logger.warning("Duplicate Gene_Name entries found in gene expression file.")

        elif file_type == 'phenotype':
            # No special validation needed at this stage
            pass
            
        self.logger.info(f"Successfully loaded {file_type} file.")
        return df
