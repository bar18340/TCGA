# tcga/data/file_handler.py

import os
import pandas as pd
import re
from tcga.utils.logger import setup_logger

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

    def upload_file(self, file_path, file_type):
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
                self.methylation_df = df
                self.logger.info(f"Successfully uploaded methylation file '{file_name}'.")
            elif file_type == 'gene_mapping':
                # Read the gene mapping file as TSV with UTF-8 encoding, ensure it has at least two columns
                df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
                if df.shape[1] < 2:
                    error_message = f"Gene mapping file '{file_name}' must have at least two columns."
                    self.logger.error(error_message)
                    raise ValueError(error_message)
                # Assume first column is gene code name and second column is actual gene name
                df = df.iloc[:, :2]
                df.columns = ['Gene_Code', 'Actual_Gene_Name']  # Standardize column names
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

    def merge_files(self, zero_percent=0):
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
            # Ensure the first column in methylation_df is 'Gene_Code'
            if self.methylation_df.columns[0].lower() != 'gene_code':
                self.methylation_df = self.methylation_df.rename(columns={self.methylation_df.columns[0]: 'Gene_Code'})
                self.logger.info("Renamed first column of methylation data to 'Gene_Code'.")

            # Merge on 'Gene_Code'
            merged_df = pd.merge(self.methylation_df, self.gene_mapping_df, on='Gene_Code', how='left')

            # Reorder columns: 'Gene_Code', 'Actual_Gene_Name', followed by the rest
            cols = merged_df.columns.tolist()
            gene_code_index = cols.index('Gene_Code')
            actual_gene_name = 'Actual_Gene_Name'

            # Remove 'Actual_Gene_Name' from its current position
            cols.remove(actual_gene_name)
            # Insert 'Actual_Gene_Name' right after 'Gene_Code'
            cols.insert(gene_code_index + 1, actual_gene_name)

            # Reorder the DataFrame
            merged_df = merged_df[cols]

            # Debug: Log column names
            self.logger.debug(f"DataFrame columns after merging: {merged_df.columns.tolist()}")

            # Debug: Log the first few rows
            self.logger.debug(f"Merged DataFrame preview:\n{merged_df.head()}")

            # Clean the merged DataFrame without the workaround
            cleaned_df, rows_removed = self.clean_merged_df(merged_df, zero_percent=zero_percent)

            if rows_removed > 0:
                self.logger.info(f"Removed {rows_removed} rows exceeding {zero_percent}% zeros.")

            self.logger.info("Merging and cleaning completed successfully.")
            return cleaned_df, rows_removed

        except Exception as e:
            error_message = f"Error during merging: {e}"
            self.logger.error(error_message)
            raise ValueError(error_message)

    def clean_merged_df(self, merged_df, zero_percent=0):
        """
        Cleans the merged DataFrame by:
        1. Removing rows where 'Actual_Gene_Name' is '.'.
        2. Replacing 'NA', 'na', '.', and 0 with NaN in data columns.
        3. Dropping rows where all data columns are NaN.
        4. Converting data columns to numeric types.
        5. Replacing remaining NaN values with 0.
        6. Removing rows exceeding the specified percentage of zeros.

        Parameters:
            merged_df (DataFrame): The merged pandas DataFrame.
            zero_percent (float): The maximum allowable percentage of zeros in any row.

        Returns:
            tuple: (cleaned DataFrame, number of rows removed)
        """
        # Initial row count
        initial_row_count = merged_df.shape[0]

        # 1. Remove rows where 'Actual_Gene_Name' is exactly '.'
        condition_dot = merged_df['Actual_Gene_Name'] == '.'
        rows_removed_dot = condition_dot.sum()
        cleaned_df = merged_df[~condition_dot]
        self.logger.debug(f"Removed {rows_removed_dot} rows where 'Actual_Gene_Name' is '.'.")

        # 2. Define data columns (excluding 'Gene_Code' and 'Actual_Gene_Name')
        data_columns = [col for col in cleaned_df.columns if col not in ['Gene_Code', 'Actual_Gene_Name']]

        # 3. Replace 'NA', 'na', '.', and 0 with NaN in data columns
        cleaned_df.loc[:, data_columns] = cleaned_df[data_columns].replace(['NA', 'na', '.', 0], pd.NA)
        self.logger.debug("Replaced 'NA', 'na', '.', and 0 with NaN in data columns.")

        # 4. Drop rows where all data columns are NaN
        condition_all_empty = cleaned_df[data_columns].isna().all(axis=1)
        rows_removed_empty = condition_all_empty.sum()
        cleaned_df = cleaned_df[~condition_all_empty]
        self.logger.debug(f"Removed {rows_removed_empty} rows where all data columns are empty, 'NA', 'na', '.', or 0.")

        # 5. Convert data columns to numeric types, coercing errors to NaN
        cleaned_df[data_columns] = cleaned_df[data_columns].apply(pd.to_numeric, errors='coerce')
        self.logger.debug("Converted data columns to numeric types, coercing errors to NaN.")

        # 6. Replace remaining NaN values in data columns with 0
        cleaned_df.loc[:, data_columns] = cleaned_df[data_columns].fillna(0)
        self.logger.debug("Replaced remaining missing values in data columns with 0.")

        # 7. Calculate the percentage of zeros in each row
        zero_counts = (cleaned_df[data_columns] == 0).sum(axis=1)
        total_data_columns = len(data_columns)
        zero_percentage = (zero_counts / total_data_columns) * 100

        # 8. Remove rows where zero_percentage >= zero_percent
        condition_exceed_zero = zero_percentage >= zero_percent
        rows_removed_threshold = condition_exceed_zero.sum()
        cleaned_df = cleaned_df[~condition_exceed_zero]
        self.logger.debug(f"Removed {rows_removed_threshold} rows exceeding {zero_percent}% zeros.")

        # Final row count
        final_row_count = cleaned_df.shape[0]
        total_rows_removed = rows_removed_dot + rows_removed_empty + rows_removed_threshold

        self.logger.debug(f"Initial rows: {initial_row_count}, after cleaning: {final_row_count}, total removed: {total_rows_removed}")

        return cleaned_df, total_rows_removed

    def cleanup(self):
        """
        Performs any necessary cleanup actions.
        Currently, no temporary files or directories are handled.
        """
        self.logger.debug("Cleanup called. No temporary files to remove.")
        pass
