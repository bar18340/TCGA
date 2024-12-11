# tcga/data/file_handler.py

import os
import pandas as pd
from tcga.utils.logger import setup_logger

class FileHandler:
    def __init__(self, logger):
        self.methylation_df = None  # DataFrame for methylation data
        self.gene_mapping_df = None  # DataFrame for gene mapping data
        self.logger = logger  # Use the passed logger

    def upload_file(self, file_path, file_type):
        """
        Uploads a file and stores its DataFrame based on the file type.

        Parameters:
            file_path (str): The path to the file.
            file_type (str): Type of the file ('methylation' or 'gene_mapping').

        Returns:
            str: The name of the uploaded file.
        """
        if not os.path.exists(file_path):
            self.logger.error(f"The file '{file_path}' does not exist.")
            raise FileNotFoundError(f"The file '{file_path}' does not exist.")

        file_name = os.path.basename(file_path)
        self.logger.info(f"Uploading {file_type} file: {file_name}")

        try:
            if file_type == 'methylation':
                # Read the file as TSV
                df = pd.read_csv(file_path, sep='\t')
                self.methylation_df = df
                self.logger.info(f"Successfully uploaded methylation file '{file_name}'.")
            elif file_type == 'gene_mapping':
                # Read the gene mapping file as TSV, ensure it has at least two columns
                df = pd.read_csv(file_path, sep='\t')
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

            # No preview as per new requirements

            return file_name
        except pd.errors.ParserError as pe:
            error_message = f"Failed to parse '{file_name}' as TSV: {pe}"
            self.logger.error(error_message)
            raise ValueError(error_message)
        except Exception as e:
            error_message = f"Error reading '{file_name}': {e}"
            self.logger.error(error_message)
            raise ValueError(error_message)

    def merge_files(self):
        """
        Merges methylation data with gene mapping data based on gene code names.

        Returns:
            DataFrame: The merged DataFrame with an additional 'Actual_Gene_Name' column.

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
            # Assuming the first column in methylation_df is 'Gene_Code'
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

            # Check for any missing gene names
            missing_gene_names = merged_df['Actual_Gene_Name'].isnull().sum()
            if missing_gene_names > 0:
                self.logger.warning(f"There are {missing_gene_names} genes without mapping in the gene mapping file.")

            self.logger.info("Merging completed successfully.")
            return merged_df
        except Exception as e:
            error_message = f"Error during merging: {e}"
            self.logger.error(error_message)
            raise ValueError(error_message)

    def cleanup(self):
        # If you have temporary directories or files, handle cleanup here
        self.logger.debug("Cleanup called. No temporary files to remove.")
        pass
