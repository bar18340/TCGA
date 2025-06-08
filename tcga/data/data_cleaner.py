import polars as pl
from tcga.utils.logger import setup_logger

class DataCleaner:
    def __init__(self, logger=None):
        self.logger = logger if logger else setup_logger()

    def clean_merged_df(self, merged_df: pl.DataFrame, zero_percent: float = 0) -> tuple:
        initial_row_count = merged_df.shape[0]
        self.logger.debug(f"Initial rows: {initial_row_count}")

        filtered_df = merged_df.filter(pl.col("Actual_Gene_Name") != ".")
        rows_removed_dot = initial_row_count - filtered_df.shape[0]

        data_columns = [col for col in filtered_df.columns if col not in ('Gene_Code', 'Actual_Gene_Name')]
        self.logger.debug(f"Data columns identified for cleaning: {data_columns}")

        cleaned_df = filtered_df.with_columns([
            pl.when(pl.col(col).cast(pl.Utf8).is_in(["NA", "na", "."]))
            .then(None)
            .otherwise(pl.col(col))
            .cast(pl.Float64)
            .fill_null(0.0)
            .alias(col)
            for col in data_columns
        ])

        zero_sum_expr = sum([pl.col(col) == 0 for col in data_columns])
        zero_mask = cleaned_df.select(zero_sum_expr)
        row_zero_percent = zero_mask.to_series() / len(data_columns) * 100
        keep_mask = row_zero_percent < zero_percent
        retained_df = cleaned_df.filter(keep_mask)
        rows_removed_threshold = cleaned_df.shape[0] - retained_df.shape[0]

        final_row_count = retained_df.shape[0]
        total_rows_removed = rows_removed_dot + rows_removed_threshold
        self.logger.debug(f"Final rows: {final_row_count}, Total rows removed: {total_rows_removed}")

        return retained_df, total_rows_removed

    def clean_gene_expression_df(self, gene_expression_df: pl.DataFrame, zero_percent: float = 0) -> tuple:
        initial_row_count = gene_expression_df.shape[0]
        self.logger.debug(f"Initial rows in Gene Expression DataFrame: {initial_row_count}")

        gene_col = gene_expression_df.columns[0]
        data_columns = gene_expression_df.columns[1:]

        filtered_df = gene_expression_df.filter(
            pl.col(gene_col).is_not_null() & (pl.col(gene_col).cast(pl.Utf8).str.strip_chars() != "")
        )
        rows_removed_invalid = initial_row_count - filtered_df.shape[0]

        cleaned_df = filtered_df.with_columns([
            pl.when(pl.col(col).cast(pl.Utf8).is_in(["NA", "na", "."]))
            .then(0.0)
            .otherwise(pl.col(col).cast(pl.Float64))
            .alias(col)
            for col in data_columns
        ])

        zero_sum_expr = sum([pl.col(col) == 0 for col in data_columns])
        zero_mask = cleaned_df.select(zero_sum_expr)
        row_zero_percent = zero_mask.to_series() / len(data_columns) * 100
        keep_mask = row_zero_percent < zero_percent
        retained_df = cleaned_df.filter(keep_mask)
        rows_removed_threshold = cleaned_df.shape[0] - retained_df.shape[0]

        final_row_count = retained_df.shape[0]
        total_rows_removed = rows_removed_invalid + rows_removed_threshold
        self.logger.debug(f"Final rows in Gene Expression DataFrame: {final_row_count}, Total rows removed: {total_rows_removed}")

        return retained_df, total_rows_removed
