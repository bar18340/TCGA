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
        self.methylation_df = None
        self.gene_mapping_df = None
        self.gene_expression_df = None
        self.phenotype_df = None
        self.logger = logger if logger else setup_logger()
        self.merger = DataMerger(logger=self.logger)
        self.cleaner = DataCleaner(logger=self.logger)

    def upload_file(self, file_path: str, file_type: str) -> str:
        """
        Uploads and prepares a file for processing based on its type.

        Reads the file using Polars, infers schema, and sanitizes columns as needed.
        Handles methylation, gene mapping, gene expression, and phenotype files.

        Args:
            file_path (str): Path to the file to upload.
            file_type (str): Type of the file ('methylation', 'gene_mapping', 'gene_expression', 'phenotype').

        Returns:
            str: The name of the uploaded file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is invalid or contains duplicate/incorrect columns.
        """
        if not os.path.exists(file_path):
            self.logger.error(f"The file '{file_path}' does not exist.")
            raise FileNotFoundError(f"The file '{file_path}' does not exist.")

        file_name = os.path.basename(file_path)
        self.logger.info(f"Uploading {file_type} file: {file_name}")

        try:
            df = pl.read_csv(
                file_path,
                separator='\t',
                infer_schema_length=10000,
                ignore_errors=True
            )

            # Handle methylation file
            if file_type == 'methylation':
                first_col = df.columns[0].strip().lower()
                if first_col != 'gene_code':
                    original_first_col = df.columns[0]
                    df = df.rename({original_first_col: 'Gene_Code'})
                    self.logger.info(f"Renamed column '{original_first_col}' to 'Gene_Code'.")
                else:
                    df = df.rename({df.columns[0]: 'Gene_Code'})
                self.logger.debug(f"Methylation DataFrame columns after processing: {df.columns}")
                self.methylation_df = df
                self.logger.info(f"Successfully uploaded methylation file '{file_name}'.")

            # Handle gene mapping file
            elif file_type == 'gene_mapping':
                if df.shape[1] < 2:
                    error_message = f"Gene mapping file '{file_name}' must have at least two columns."
                    self.logger.error(error_message)
                    raise ValueError(error_message)
                df = df.select([df.columns[0], df.columns[1]]).rename({
                    df.columns[0]: 'Gene_Code',
                    df.columns[1]: 'Actual_Gene_Name'
                })
                if df.select('Gene_Code').is_duplicated().any():
                    duplicates = df.filter(pl.col('Gene_Code').is_duplicated()).select('Gene_Code').unique()
                    duplicate_list = duplicates.to_series().to_list()
                    error_message = f"Gene mapping file '{file_name}' contains duplicate Gene_Code entries: {', '.join(duplicate_list)}"
                    self.logger.error(error_message)
                    raise ValueError(error_message)
                self.gene_mapping_df = df
                self.logger.info(f"Successfully uploaded gene mapping file '{file_name}'.")
            
            # Handle gene expression file
            elif file_type == 'gene_expression':
                first_col = df.columns[0].strip().lower()
                if first_col != 'gene_name':
                    original_first_col = df.columns[0]
                    df = df.rename({original_first_col: 'Gene_Name'})
                    self.logger.info(f"Renamed column '{original_first_col}' to 'Gene_Name'.")
                else:
                    df = df.rename({df.columns[0]: 'Gene_Name'})
                if df.select('Gene_Name').is_duplicated().any():
                    duplicates = df.filter(pl.col('Gene_Name').is_duplicated()).select('Gene_Name').unique()
                    duplicate_list = duplicates.to_series().to_list()
                    error_message = f"Gene expression file '{file_name}' contains duplicate Gene_Name entries: {', '.join(map(str, duplicate_list))}"
                    self.logger.error(error_message)
                    raise ValueError(error_message)
                self.gene_expression_df = df
                self.logger.info(f"Successfully uploaded gene expression file '{file_name}'.")

            # Handle phenotype file
            elif file_type == 'phenotype':
                self.phenotype_df = df
                self.logger.info(f"Successfully uploaded phenotype file '{file_name}'.")

            else:
                error_message = f"Unknown file type: {file_type}"
                self.logger.error(error_message)
                raise ValueError(error_message)

            return file_name

        except Exception as e:
            error_message = f"Error reading '{file_name}': {e}"
            self.logger.error(error_message)
            raise ValueError(error_message)

    def merge_files(self, zero_percent: float = 0) -> tuple:
        """
        Cleans and merges methylation and gene mapping files.

        Args:
            zero_percent (float): Threshold for filtering rows with excessive zero values.

        Returns:
            tuple: (cleaned DataFrame, number of rows removed)

        Raises:
            ValueError: If required files are missing or merging fails.
        """
        if self.methylation_df is None:
            raise ValueError("No methylation file uploaded. Please upload a methylation file.")
        if self.gene_mapping_df is None:
            raise ValueError("No gene mapping file uploaded. Please upload a gene mapping file.")

        self.logger.info("Merging methylation data with gene mapping data.")
        try:
            cleaned_df, rows_removed = self.merger.merge_and_clean(
                methylation_df=self.methylation_df,
                gene_mapping_df=self.gene_mapping_df,
                zero_percent=zero_percent
            )
            return cleaned_df, rows_removed
        except Exception as e:
            raise ValueError(f"Error during merging and cleaning: {e}")

    def clean_gene_expression_df(self, zero_percent: float = 0) -> tuple:
        """
        Cleans the gene expression file based on a zero-value threshold.

        Args:
            zero_percent (float): Threshold for filtering rows with excessive zero values.

        Returns:
            tuple: (cleaned DataFrame, number of rows removed)

        Raises:
            ValueError: If the gene expression file is missing or cleaning fails.
        """
        if self.gene_expression_df is None:
            raise ValueError("No gene expression file uploaded. Please upload a gene expression file.")
        try:
            cleaned_df, rows_removed = self.cleaner.clean_gene_expression_df(
                self.gene_expression_df, zero_percent=zero_percent)
            return cleaned_df, rows_removed
        except Exception as e:
            raise ValueError(f"Error cleaning gene expression data: {e}")

    def cleanup(self):
        """
        Cleans up any resources or temporary files used by the FileHandler instance.

        This method is a placeholder for future cleanup logic. Currently, it does not remove any files,
        but it can be extended to handle deletion of temporary files or other resource management tasks
        as needed.
        """
        self.logger.debug("Cleanup called. No temporary files to remove.")
        pass
