# tcga/data/file_handler.py

import os
import pandas as pd
from tcga.utils.logger import setup_logger
from tcga.data.data_merger import DataMerger

class FileHandler:
    def __init__(self, logger=None):
        """
        Initializes the FileHandler with an optional custom logger.
        If no logger is provided, sets up a default logger.

        Parameters:
            logger (logging.Logger, optional): Custom logger. Defaults to None.
        """
        self.methylation_df = None  # DataFrame for methylation data
        self.gene_mapping_df = None  # DataFrame for gene mapping data
        self.logger = logger if logger else setup_logger()
        self.merger = DataMerger(logger=self.logger)  # Initialize DataMerger

    def upload_file(self, file_path: str, file_type: str) -> str:
        """
        Uploads a file and stores its DataFrame based on the file type.

        Parameters:
            file_path (str): The path to the file.
            file_type (str): Type of the file ('methylation' or 'gene_mapping').

        Returns:
            str: The name of the uploaded file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file type is unknown or if gene mapping file has insufficient columns or duplicates.
        """
        if not os.path.exists(file_path):
            self.logger.error(f"The file '{file_path}' does not exist.")
            raise FileNotFoundError(f"The file '{file_path}' does not exist.")

        file_name = os.path.basename(file_path)
        self.logger.info(f"Uploading {file_type} file: {file_name}")

        try:
            if file_type == 'methylation':
                # Read the file as TSV with UTF-8 encoding
                df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
                self.logger.debug(f"Methylation DataFrame columns before processing: {df.columns.tolist()}")

                # Ensure the first column is 'Gene_Code' (case-insensitive and trimmed)
                first_col = df.columns[0].strip().lower()
                if first_col != 'gene_code':
                    original_first_col = df.columns[0]
                    df = df.rename(columns={original_first_col: 'Gene_Code'})
                    self.logger.info(f"Renamed column '{original_first_col}' to 'Gene_Code'.")
                else:
                    self.logger.debug("'Gene_Code' column already exists in methylation DataFrame.")

                self.logger.debug(f"Methylation DataFrame columns after processing: {df.columns.tolist()}")
                self.methylation_df = df
                self.logger.info(f"Successfully uploaded methylation file '{file_name}'.")

            elif file_type == 'gene_mapping':
                # Read the gene mapping file as TSV with UTF-8 encoding, ensure it has at least two columns
                df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
                self.logger.debug(f"Gene Mapping DataFrame columns before processing: {df.columns.tolist()}")
                if df.shape[1] < 2:
                    error_message = f"Gene mapping file '{file_name}' must have at least two columns."
                    self.logger.error(error_message)
                    raise ValueError(error_message)
                # Assume first column is gene code name and second column is actual gene name
                df = df.iloc[:, :2]
                df.columns = ['Gene_Code', 'Actual_Gene_Name']  # Standardize column names
                self.logger.debug(f"Gene Mapping DataFrame columns after renaming: {df.columns.tolist()}")

                # Check for duplicate Gene_Code entries
                if df['Gene_Code'].duplicated().any():
                    duplicate_genes = df[df['Gene_Code'].duplicated()]['Gene_Code'].unique()
                    error_message = f"Gene mapping file '{file_name}' contains duplicate Gene_Code entries: {', '.join(duplicate_genes)}"
                    self.logger.error(error_message)
                    raise ValueError(error_message)
                self.gene_mapping_df = df
                self.logger.info(f"Successfully uploaded gene mapping file '{file_name}'.")

            else:
                error_message = f"Unknown file type: {file_type}"
                self.logger.error(error_message)
                raise ValueError(error_message)

            return file_name

        except pd.errors.ParserError as pe:
            error_message = f"Failed to parse '{file_name}' as TSV: {pe}"
            self.logger.error(error_message)
            raise ValueError(error_message)
        except Exception as e:
            error_message = f"Error reading '{file_name}': {e}"
            self.logger.error(error_message)
            raise ValueError(error_message)

    def merge_files(self, zero_percent: float = 0) -> tuple:
        """
        Merges methylation data with gene mapping data based on gene code names.

        Parameters:
            zero_percent (float): The maximum allowable percentage of zeros in any row.

        Returns:
            tuple: (cleaned DataFrame, number of rows removed)

        Raises:
            ValueError: If required files are missing or merging fails.
        """
        if self.methylation_df is None:
            error_message = "No methylation file uploaded. Please upload a methylation file."
            self.logger.error(error_message)
            raise ValueError(error_message)
        if self.gene_mapping_df is None:
            error_message = "No gene mapping file uploaded. Please upload a gene mapping file."
            self.logger.error(error_message)
            raise ValueError(error_message)

        self.logger.info("Merging methylation data with gene mapping data.")

        try:
            # Use DataMerger to merge and clean the data
            cleaned_df, rows_removed = self.merger.merge_and_clean(
                methylation_df=self.methylation_df,
                gene_mapping_df=self.gene_mapping_df,
                zero_percent=zero_percent
            )

            if rows_removed > 0:
                self.logger.info(f"Removed {rows_removed} rows exceeding {zero_percent}% zeros.")

            self.logger.info("Merging and cleaning completed successfully.")
            return cleaned_df, rows_removed

        except Exception as e:
            error_message = f"Error during merging and cleaning: {e}"
            self.logger.error(error_message)
            raise ValueError(error_message)

    def cleanup(self):
        """
        Performs any necessary cleanup actions.
        Currently, no temporary files or directories are handled.
        """
        self.logger.debug("Cleanup called. No temporary files to remove.")
        pass
