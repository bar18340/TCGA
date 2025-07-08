import polars as pl
from tcga.utils.logger import setup_logger

class DataCleaner:
    """
    Provides methods for cleaning and filtering TCGA data files.

    This class includes utilities to clean merged methylation/mapping DataFrames and gene expression DataFrames,
    handling missing values, invalid gene names, and filtering rows based on a zero-value threshold.
    """

    def __init__(self, logger=None):
        """
        Initializes the DataCleaner instance.
        """
        self.logger = logger if logger else setup_logger()

    def filter_by_zero_percentage(self, df: pl.DataFrame, zero_percent: float, id_cols: list) -> pl.DataFrame:
        """
        Public method to filter ANY DataFrame based on the percentage of zero values.
        """
        if zero_percent >= 100 or df is None:
            return df
            
        data_columns = [c for c in df.columns if c not in id_cols]
        if not data_columns:
            return df

        self.logger.debug(f"Filtering rows with >={zero_percent}% zeros.")
        
        zero_sum_expr = sum(pl.col(col) == 0 for col in data_columns)
        row_zero_percent = (zero_sum_expr / len(data_columns)) * 100
        
        keep_mask = row_zero_percent < zero_percent
        # If the threshold is 0, the condition becomes "keep if percentage is exactly 0".
        if zero_percent == 0:
            keep_mask = row_zero_percent == 0

        retained_df = df.filter(keep_mask)
        
        rows_removed = df.shape[0] - retained_df.shape[0]
        if rows_removed > 0:
            self.logger.info(f"Removed {rows_removed} rows based on zero threshold.")
            
        return retained_df
    
    def clean_merged_df(self, merged_df: pl.DataFrame) -> pl.DataFrame:
        """
        Cleans a merged methylation and mapping DataFrame.

        - Removes rows where 'Actual_Gene_Name' is '.'.
        - Converts None values to 0.0 in data columns.
        """
        # 1. Remove rows with invalid gene names
        cleaned_df = merged_df.filter(pl.col("Actual_Gene_Name") != ".")
        
        # 2. Identify patient data columns
        data_columns = [col for col in cleaned_df.columns if col not in ('Gene_Code', 'Actual_Gene_Name')]

        # 3. For each data column, replace '.' with null, then cast the whole column to float,
        cleaning_expressions = [
            pl.when(pl.col(c).cast(pl.Utf8) == ".")
                .then(None)
                .otherwise(pl.col(c))
                .cast(pl.Float64, strict=False)
                .fill_null(0.0)
                .alias(c)
            for c in data_columns
        ]

        cleaned_df = cleaned_df.with_columns(cleaning_expressions)
        return cleaned_df

