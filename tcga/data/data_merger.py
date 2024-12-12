# tcga/data/data_merger.py

import pandas as pd
from tcga.utils.logger import setup_logger
from tcga.data.data_cleaner import DataCleaner

class DataMerger:
    def __init__(self, logger=None):
        """
        Initializes the DataMerger with an optional custom logger.
        If no logger is provided, sets up a default logger.

        Parameters:
            logger (logging.Logger, optional): Custom logger. Defaults to None.
        """
        self.logger = logger if logger else setup_logger()
        self.cleaner = DataCleaner(logger=self.logger)

    def merge_and_clean(self, methylation_df: pd.DataFrame, gene_mapping_df: pd.DataFrame, zero_percent: float = 0) -> tuple:
        """
        Merges methylation and gene mapping DataFrames and cleans the merged DataFrame.

        Parameters:
            methylation_df (pd.DataFrame): The methylation DataFrame.
            gene_mapping_df (pd.DataFrame): The gene mapping DataFrame.
            zero_percent (float): The maximum allowable percentage of zeros in any row.

        Returns:
            tuple: (cleaned DataFrame, number of rows removed)

        Raises:
            ValueError: If merging fails due to missing columns or other issues.
        """
        try:
            self.logger.info("Starting the merging process.")

            # Ensure 'Gene_Code' exists in both DataFrames
            if 'Gene_Code' not in methylation_df.columns:
                error_message = "'Gene_Code' column missing in methylation DataFrame."
                self.logger.error(error_message)
                raise ValueError(error_message)
            if 'Gene_Code' not in gene_mapping_df.columns:
                error_message = "'Gene_Code' column missing in gene mapping DataFrame."
                self.logger.error(error_message)
                raise ValueError(error_message)

            # Merge on 'Gene_Code' with a left join
            merged_df = pd.merge(methylation_df, gene_mapping_df, on='Gene_Code', how='left')
            self.logger.debug("DataFrames merged successfully on 'Gene_Code'.")

            # Reorder columns: 'Gene_Code', 'Actual_Gene_Name', followed by the rest
            cols = merged_df.columns.tolist()
            gene_code_index = cols.index('Gene_Code')
            actual_gene_name = 'Actual_Gene_Name'

            if actual_gene_name in cols:
                cols.remove(actual_gene_name)
                cols.insert(gene_code_index + 1, actual_gene_name)
                merged_df = merged_df[cols]
                self.logger.debug("Reordered columns to place 'Actual_Gene_Name' after 'Gene_Code'.")
            else:
                self.logger.warning(f"'{actual_gene_name}' column not found in merged DataFrame.")

            # Delegate cleaning to DataCleaner
            cleaned_df, rows_removed = self.cleaner.clean_merged_df(merged_df, zero_percent=zero_percent)
            self.logger.info("Data cleaning completed.")

            return cleaned_df, rows_removed

        except Exception as e:
            error_message = f"Error during merging and cleaning: {e}"
            self.logger.error(error_message)
            raise ValueError(error_message)
