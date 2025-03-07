# tcga/data/data_cleaner.py

import pandas as pd
import numpy as np
from tcga.utils.logger import setup_logger

class DataCleaner:
    def __init__(self, logger=None):
        self.logger = logger if logger else setup_logger()

    def clean_merged_df(self, merged_df: pd.DataFrame, zero_percent: float = 0) -> tuple:
        # Existing cleaning steps for merged methylation data
        initial_row_count = merged_df.shape[0]
        self.logger.debug(f"Initial rows: {initial_row_count}")

        condition_dot = merged_df['Actual_Gene_Name'] == '.'
        rows_removed_dot = condition_dot.sum()
        cleaned_df = merged_df[~condition_dot]
        self.logger.debug(f"Removed {rows_removed_dot} rows where 'Actual_Gene_Name' is '.'")

        data_columns = [col for col in cleaned_df.columns if col not in ['Gene_Code', 'Actual_Gene_Name']]
        self.logger.debug(f"Data columns identified for cleaning: {data_columns}")

        replacements = ['NA', 'na', '.', 0]
        cleaned_df[data_columns] = cleaned_df[data_columns].replace(replacements, np.nan)
        self.logger.debug(f"Replaced {replacements} with NaN in data columns.")

        condition_all_empty = cleaned_df[data_columns].isna().all(axis=1)
        rows_removed_empty = condition_all_empty.sum()
        cleaned_df = cleaned_df[~condition_all_empty]
        self.logger.debug(f"Removed {rows_removed_empty} rows where all data columns are NaN.")

        cleaned_df[data_columns] = cleaned_df[data_columns].apply(pd.to_numeric, errors='coerce')
        self.logger.debug("Converted data columns to numeric types, coercing errors to NaN.")

        cleaned_df[data_columns] = cleaned_df[data_columns].fillna(0)
        self.logger.debug("Replaced remaining NaN values with 0 in data columns.")

        zero_counts = (cleaned_df[data_columns] == 0).sum(axis=1)
        total_data_columns = len(data_columns)
        zero_percentage = (zero_counts / total_data_columns) * 100
        self.logger.debug("Calculated percentage of zeros in each row.")

        condition_exceed_zero = zero_percentage >= zero_percent
        rows_removed_threshold = condition_exceed_zero.sum()
        cleaned_df = cleaned_df[~condition_exceed_zero]
        self.logger.debug(f"Removed {rows_removed_threshold} rows exceeding {zero_percent}% zeros.")

        final_row_count = cleaned_df.shape[0]
        total_rows_removed = rows_removed_dot + rows_removed_empty + rows_removed_threshold
        self.logger.debug(f"Final rows: {final_row_count}, Total rows removed: {total_rows_removed}")

        return cleaned_df, total_rows_removed

    def clean_gene_expression_df(self, gene_expression_df: pd.DataFrame, zero_percent: float = 0) -> tuple:
        """
        Cleans the Gene Expression DataFrame.
        Assumes the first column contains gene identifiers and the remaining columns are patient data.
        """
        initial_row_count = gene_expression_df.shape[0]
        self.logger.debug(f"Initial rows in Gene Expression DataFrame: {initial_row_count}")

        # Remove rows where the gene identifier (first column) is missing or empty
        condition_invalid = gene_expression_df.iloc[:, 0].isna() | (gene_expression_df.iloc[:, 0].astype(str).str.strip() == '')
        rows_removed_invalid = condition_invalid.sum()
        cleaned_df = gene_expression_df[~condition_invalid]
        self.logger.debug(f"Removed {rows_removed_invalid} rows with invalid gene identifiers.")

        # Data columns: all columns except the first one
        data_columns = gene_expression_df.columns[1:]
        self.logger.debug(f"Data columns for Gene Expression cleaning: {list(data_columns)}")

        replacements = ['NA', 'na', '.', 0]
        cleaned_df.loc[:, data_columns] = cleaned_df.loc[:, data_columns].replace(replacements, np.nan)
        self.logger.debug(f"Replaced {replacements} with NaN in Gene Expression data columns.")

        condition_all_empty = cleaned_df.loc[:, data_columns].isna().all(axis=1)
        rows_removed_all_empty = condition_all_empty.sum()
        cleaned_df = cleaned_df[~condition_all_empty]
        self.logger.debug(f"Removed {rows_removed_all_empty} rows where all Gene Expression data columns are NaN.")

        cleaned_df.loc[:, data_columns] = cleaned_df.loc[:, data_columns].apply(pd.to_numeric, errors='coerce')
        self.logger.debug("Converted Gene Expression data columns to numeric types, coercing errors to NaN.")

        cleaned_df.loc[:, data_columns] = cleaned_df.loc[:, data_columns].fillna(0)
        self.logger.debug("Replaced remaining NaN values with 0 in Gene Expression data columns.")

        zero_counts = (cleaned_df.loc[:, data_columns] == 0).sum(axis=1)
        total_data_columns = len(data_columns)
        zero_percentage = (zero_counts / total_data_columns) * 100
        self.logger.debug("Calculated percentage of zeros in each Gene Expression row.")

        condition_exceed = zero_percentage >= zero_percent
        rows_removed_threshold = condition_exceed.sum()
        cleaned_df = cleaned_df[~condition_exceed]
        self.logger.debug(f"Removed {rows_removed_threshold} Gene Expression rows exceeding {zero_percent}% zeros.")

        final_row_count = cleaned_df.shape[0]
        total_rows_removed = rows_removed_invalid + rows_removed_all_empty + rows_removed_threshold
        self.logger.debug(f"Final rows in Gene Expression DataFrame: {final_row_count}, Total rows removed: {total_rows_removed}")

        return cleaned_df, total_rows_removed
