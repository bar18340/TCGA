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
    Supports both CSV/TSV and Excel file formats.
    """

    def __init__(self, logger=None):
        """
        Initializes the FileHandler instance.
        """
        self.logger = logger if logger else setup_logger()

    def _detect_file_format(self, file_path: str) -> str:
        """
        Detects the file format based on file extension.
        
        Returns:
            str: 'excel' for Excel files, 'csv' for CSV/TSV files
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            return 'excel'
        return 'csv'

    def _read_file(self, file_path: str) -> pl.DataFrame:
        """
        Reads a file based on its format (CSV/TSV or Excel).
        
        Args:
            file_path: Path to the file
            
        Returns:
            pl.DataFrame: The loaded dataframe
        """
        file_format = self._detect_file_format(file_path)
        
        if file_format == 'excel':
            # Read Excel file
            self.logger.info(f"Reading Excel file: {os.path.basename(file_path)}")
            try:
                # Try reading with xlsx2csv engine first (faster)
                df = pl.read_excel(
                    file_path, 
                    sheet_id=1,  # Read first sheet
                    engine='xlsx2csv',
                    infer_schema_length=10000
                )
            except Exception as e:
                self.logger.warning(f"xlsx2csv engine failed: {e}, trying openpyxl")
                try:
                    # Fallback to openpyxl
                    df = pl.read_excel(
                        file_path,
                        sheet_id=1,
                        engine='openpyxl'
                    )
                except Exception as e2:
                    self.logger.warning(f"openpyxl engine failed: {e2}, trying default")
                    # Last resort - default reader
                    df = pl.read_excel(file_path)
        else:
            # Read CSV/TSV file
            self.logger.info(f"Reading CSV/TSV file: {os.path.basename(file_path)}")
            df = pl.read_csv(
                file_path, 
                separator='\t',  # Default to tab separator
                infer_schema_length=10000, 
                ignore_errors=True, 
                null_values=["NA", "na", "null", ""]
            )
            
        return df

    def load_dataframe(self, file_path: str, file_type: str) -> pl.DataFrame:
        """
        Loads a file into a Polars DataFrame and performs initial validation.
        Supports both CSV/TSV and Excel formats.
        """
        if not file_path or not os.path.exists(file_path):
            self.logger.warning(f"File path for {file_type} is missing or invalid.")
            return None

        file_name = os.path.basename(file_path)
        self.logger.info(f"Loading {file_type} file: {file_name}")

        try:
            df = self._read_file(file_path)
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

    def save_dataframe(self, df: pl.DataFrame, file_path: str, file_format: str = 'csv') -> None:
        """
        Saves a DataFrame to a file in the specified format.
        
        Args:
            df: The DataFrame to save
            file_path: Path where to save the file
            file_format: Either 'csv' or 'excel'
        """
        if file_format == 'excel':
            # Ensure the path has .xlsx extension
            if not file_path.endswith('.xlsx'):
                base = os.path.splitext(file_path)[0]
                file_path = f"{base}.xlsx"
            
            self.logger.info(f"Saving as Excel file: {os.path.basename(file_path)}")
            
            # Write to Excel preserving all data exactly as is
            df.write_excel(
                file_path,
                worksheet="Sheet1"
            )
        else:
            # Ensure the path has .csv extension
            if not file_path.endswith('.csv'):
                base = os.path.splitext(file_path)[0]
                file_path = f"{base}.csv"
                
            self.logger.info(f"Saving as CSV file: {os.path.basename(file_path)}")
            df.write_csv(file_path)