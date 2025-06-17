import polars as pl
from tcga.utils.logger import setup_logger
from tcga.data.data_cleaner import DataCleaner

class DataMerger:
    def __init__(self, logger=None):
        self.logger = logger if logger else setup_logger()
        self.cleaner = DataCleaner(logger=self.logger)

    def merge_and_clean(self, methylation_df: pl.DataFrame, gene_mapping_df: pl.DataFrame, zero_percent: float = 0) -> tuple:
        try:
            self.logger.info("Starting the merging process.")

            if 'Gene_Code' not in methylation_df.columns:
                error_message = "'Gene_Code' column missing in methylation DataFrame."
                self.logger.error(error_message)
                raise ValueError(error_message)
            if 'Gene_Code' not in gene_mapping_df.columns:
                error_message = "'Gene_Code' column missing in gene mapping DataFrame."
                self.logger.error(error_message)
                raise ValueError(error_message)

            # Ensure both are strings
            methylation_df = methylation_df.with_columns([
                pl.col("Gene_Code").cast(pl.Utf8).alias("Gene_Code")
            ])
            gene_mapping_df = gene_mapping_df.with_columns([
                pl.col("Gene_Code").cast(pl.Utf8).alias("Gene_Code")
            ])

            # Check for duplicate gene codes in gene mapping
            if gene_mapping_df.select("Gene_Code").is_duplicated().any():
                duplicates = gene_mapping_df.filter(pl.col("Gene_Code").is_duplicated()).select("Gene_Code").unique()
                duplicate_list = duplicates.to_series().to_list()
                error_message = f"Gene mapping contains duplicate Gene_Code entries: {', '.join(duplicate_list)}"
                self.logger.error(error_message)
                raise ValueError(error_message)

            # Merge on 'Gene_Code'
            merged_df = methylation_df.join(gene_mapping_df, on='Gene_Code', how='left')
            self.logger.debug("DataFrames merged successfully on 'Gene_Code'.")

            # Reorder columns: 'Gene_Code', 'Actual_Gene_Name', followed by the rest
            cols = merged_df.columns
            actual_gene_name = "Actual_Gene_Name"

            if actual_gene_name in cols:
                cols = ["Gene_Code", "Actual_Gene_Name"] + [col for col in cols if col not in ("Gene_Code", "Actual_Gene_Name")]
                merged_df = merged_df.select(cols)
                self.logger.debug("Reordered columns to place 'Actual_Gene_Name' after 'Gene_Code'.")
            else:
                self.logger.warning(f"'{actual_gene_name}' column not found in merged DataFrame.")

            # Clean merged data
            cleaned_df, rows_removed = self.cleaner.clean_merged_df(merged_df, zero_percent=zero_percent)
            self.logger.info("Data cleaning completed.")

            return cleaned_df, rows_removed

        except Exception as e:
            error_message = f"Error during merging and cleaning: {e}"
            self.logger.error(error_message)
            raise ValueError(error_message)
