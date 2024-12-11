# tcga/data/file_handler.py

import os
import pandas as pd
import shutil
from tcga.utils.logger import setup_logger

class FileHandler:
    def __init__(self, logger):
        self.methylation_files = {}  # Dictionary to store methylation DataFrames
        self.gene_mapping_files = {}  # Dictionary to store gene mapping DataFrames
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
                self.methylation_files[file_name] = df
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
                self.gene_mapping_files[file_name] = df
                self.logger.info(f"Successfully uploaded gene mapping file '{file_name}'.")
            else:
                error_message = f"Unknown file type: {file_type}"
                self.logger.error(error_message)
                raise ValueError(error_message)
            
            # Print preview
            self.print_preview(df, file_name)
            return file_name
        except pd.errors.ParserError as pe:
            error_message = f"Failed to parse '{file_name}' as TSV: {pe}"
            self.logger.error(error_message)
            raise ValueError(error_message)
        except Exception as e:
            error_message = f"Error reading '{file_name}': {e}"
            self.logger.error(error_message)
            raise ValueError(error_message)

    def print_preview(self, df, file_name, num_rows=5):
        """
        Prints the first few rows of the DataFrame to the console.

        Parameters:
            df (DataFrame): The pandas DataFrame.
            file_name (str): The name of the file.
            num_rows (int): Number of rows to print.
        """
        print(f"\n=== Preview of '{file_name}' ===")
        print(df.head(num_rows))
        print("==============================\n")

    def merge_files(self):
        """
        Merges methylation data with gene mapping data based on gene code names.

        Returns:
            DataFrame: The merged DataFrame with an additional 'Actual_Gene_Name' column.

        Raises:
            ValueError: If required files are missing or merging fails.
        """
        if not self.methylation_files:
            error_message = "No methylation files uploaded. Please upload at least one methylation file."
            self.logger.error(error_message)
            raise ValueError(error_message)
        if not self.gene_mapping_files:
            error_message = "No gene mapping files uploaded. Please upload at least one gene mapping file."
            self.logger.error(error_message)
            raise ValueError(error_message)

        # For simplicity, use the first uploaded methylation and gene mapping files
        # You can extend this to handle multiple files as needed
        methylation_file_name, methylation_df = next(iter(self.methylation_files.items()))
        gene_mapping_file_name, gene_mapping_df = next(iter(self.gene_mapping_files.items()))

        self.logger.info(f"Merging methylation file '{methylation_file_name}' with gene mapping file '{gene_mapping_file_name}'.")

        try:
            # Assuming the first column in methylation_df is 'Gene_Code'
            if methylation_df.columns[0].lower() != 'gene_code':
                methylation_df = methylation_df.rename(columns={methylation_df.columns[0]: 'Gene_Code'})
                self.logger.info(f"Renamed first column of methylation file '{methylation_file_name}' to 'Gene_Code'.")

            # Merge on 'Gene_Code'
            merged_df = pd.merge(methylation_df, gene_mapping_df, on='Gene_Code', how='left')

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

    def get_uploaded_files(self):
        """
        Returns a dictionary of uploaded file names categorized by file type.

        Returns:
            dict: Dictionary with keys 'methylation' and 'gene_mapping' containing lists of file names.
        """
        return {
            'methylation': list(self.methylation_files.keys()),
            'gene_mapping': list(self.gene_mapping_files.keys())
        }

    def get_file(self, file_type, file_name):
        """
        Retrieves the DataFrame associated with the given file name based on file type.

        Parameters:
            file_type (str): Type of the file ('methylation' or 'gene_mapping').
            file_name (str): The name of the file.

        Returns:
            DataFrame or None: The pandas DataFrame if exists, else None.
        """
        if file_type == 'methylation':
            return self.methylation_files.get(file_name, None)
        elif file_type == 'gene_mapping':
            return self.gene_mapping_files.get(file_name, None)
        else:
            self.logger.error(f"Unknown file type: {file_type}")
            return None

    def cleanup(self):
        # If you have temporary directories or files, handle cleanup here
        self.logger.debug("Cleanup called. No temporary files to remove.")
        pass
