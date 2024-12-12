# tcga/data/data_cleaner.py

import pandas as pd
import numpy as np
from tcga.utils.logger import setup_logger

class DataCleaner:
    def __init__(self, logger=None):
        """
        Initializes the DataCleaner with an optional custom logger.
        If no logger is provided, sets up a default logger.

        Parameters:
            logger (logging.Logger, optional): Custom logger. Defaults to None.
        """
        self.logger = logger if logger else setup_logger()

    def clean_merged_df(self, merged_df: pd.DataFrame, zero_percent: float = 0) -> tuple:
        """
        Cleans the merged DataFrame by:
        1. Removing rows where 'Actual_Gene_Name' is '.'.
        2. Replacing 'NA', 'na', '.', and 0 with NaN in data columns.
        3. Dropping rows where all data columns are NaN.
        4. Converting data columns to numeric types.
        5. Replacing remaining NaN values with 0.
        6. Removing rows exceeding the specified percentage of zeros.

        Parameters:
            merged_df (pd.DataFrame): The merged pandas DataFrame.
            zero_percent (float): The maximum allowable percentage of zeros in any row.

        Returns:
            tuple: (cleaned DataFrame, number of rows removed)
        """
        # Initial row count
        initial_row_count = merged_df.shape[0]
        self.logger.debug(f"Initial rows: {initial_row_count}")

        # 1. Remove rows where 'Actual_Gene_Name' is exactly '.'
        condition_dot = merged_df['Actual_Gene_Name'] == '.'
        rows_removed_dot = condition_dot.sum()
        cleaned_df = merged_df[~condition_dot]
        self.logger.debug(f"Removed {rows_removed_dot} rows where 'Actual_Gene_Name' is '.'")

        # 2. Define data columns (excluding 'Gene_Code' and 'Actual_Gene_Name')
        data_columns = [col for col in cleaned_df.columns if col not in ['Gene_Code', 'Actual_Gene_Name']]
        self.logger.debug(f"Data columns identified for cleaning: {data_columns}")

        # 3. Replace 'NA', 'na', '.', and 0 with NaN in data columns
        replacements = ['NA', 'na', '.', 0]
        cleaned_df[data_columns] = cleaned_df[data_columns].replace(replacements, np.nan)
        self.logger.debug(f"Replaced {replacements} with NaN in data columns.")

        # 4. Drop rows where all data columns are NaN
        condition_all_empty = cleaned_df[data_columns].isna().all(axis=1)
        rows_removed_empty = condition_all_empty.sum()
        cleaned_df = cleaned_df[~condition_all_empty]
        self.logger.debug(f"Removed {rows_removed_empty} rows where all data columns are NaN.")

        # 5. Convert data columns to numeric types, coercing errors to NaN
        cleaned_df[data_columns] = cleaned_df[data_columns].apply(pd.to_numeric, errors='coerce')
        self.logger.debug("Converted data columns to numeric types, coercing errors to NaN.")

        # 6. Replace remaining NaN values in data columns with 0
        cleaned_df[data_columns] = cleaned_df[data_columns].fillna(0)
        self.logger.debug("Replaced remaining NaN values with 0 in data columns.")

        # 7. Calculate the percentage of zeros in each row
        zero_counts = (cleaned_df[data_columns] == 0).sum(axis=1)
        total_data_columns = len(data_columns)
        zero_percentage = (zero_counts / total_data_columns) * 100
        self.logger.debug("Calculated percentage of zeros in each row.")

        # 8. Remove rows where zero_percentage >= zero_percent
        condition_exceed_zero = zero_percentage >= zero_percent
        rows_removed_threshold = condition_exceed_zero.sum()
        cleaned_df = cleaned_df[~condition_exceed_zero]
        self.logger.debug(f"Removed {rows_removed_threshold} rows exceeding {zero_percent}% zeros.")

        # Final row count
        final_row_count = cleaned_df.shape[0]
        total_rows_removed = rows_removed_dot + rows_removed_empty + rows_removed_threshold
        self.logger.debug(f"Final rows: {final_row_count}, Total rows removed: {total_rows_removed}")

        return cleaned_df, total_rows_removed
