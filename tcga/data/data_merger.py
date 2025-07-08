import polars as pl
from tcga.utils.logger import setup_logger
from tcga.data.data_cleaner import DataCleaner

class DataMerger:
    """
    Handles merging and cleaning of methylation and gene mapping DataFrames.

    This class is responsible for:
    - Validating the presence and types of required columns in both methylation and gene mapping DataFrames.
    - Ensuring 'Gene_Code' columns are present and of string type in both DataFrames.
    - Checking for and reporting duplicate 'Gene_Code' entries in the gene mapping DataFrame.
    - Merging the methylation and gene mapping DataFrames on the 'Gene_Code' column.
    - Reordering columns so that 'Gene_Code' and 'Actual_Gene_Name' appear first in the merged DataFrame.
    - Delegating further cleaning (removal of invalid rows, handling of missing values, filtering by zero threshold) to the DataCleaner class.
    """
    def __init__(self, logger=None):
        """
        Initializes the DataMerger instance.
        """
        self.logger = logger if logger else setup_logger()

    def merge(self, methylation_df: pl.DataFrame, gene_mapping_df: pl.DataFrame) -> pl.DataFrame:
        """
        Merges methylation and gene mapping DataFrames on 'Gene_Code' and cleans the result.
        """
        if 'Gene_Code' not in methylation_df.columns or 'Gene_Code' not in gene_mapping_df.columns:
            raise ValueError("Both methylation and gene mapping files must contain a 'Gene_Code' column.")

        if gene_mapping_df.select("Gene_Code").is_duplicated().any():
            duplicates = gene_mapping_df.filter(pl.col("Gene_Code").is_duplicated()).select("Gene_Code").unique()
            error_message = f"Gene mapping contains duplicate Gene_Code entries: {', '.join(map(str, duplicates.to_series().to_list()))}"
            self.logger.error(error_message)
            raise ValueError(error_message)

        merged_df = methylation_df.join(gene_mapping_df, on='Gene_Code', how='inner')

        cols = merged_df.columns
        if "Actual_Gene_Name" in cols:
            new_order = ["Gene_Code", "Actual_Gene_Name"] + [col for col in cols if col not in ["Gene_Code", "Actual_Gene_Name"]]
            merged_df = merged_df.select(new_order)
            
        return merged_df