import polars as pl
from tcga.utils.logger import setup_logger

class DataPhenotype:
    def __init__(self, logger=None):
        self.logger = logger if logger else setup_logger()

    def get_characteristics(self, phenotype_df: pl.DataFrame) -> list:
        """
        Returns all phenotype characteristics except the first column (patient IDs).
        """
        characteristics = phenotype_df.columns[1:]
        self.logger.debug(f"Extracted phenotype characteristics: {characteristics}")
        return characteristics

    def merge_into_files(self, final_meth: pl.DataFrame, final_expr: pl.DataFrame,
                         phenotype_df: pl.DataFrame, selected_chars: list) -> tuple:
        """
        Adds rows for selected phenotype characteristics to both methylation and expression files.
        Each row contains a characteristic and its values for matching patients.
        Missing values are left as empty strings.
        """
        id_col = phenotype_df.columns[0]
        phen = phenotype_df.select([id_col] + selected_chars).with_columns([
            pl.col(id_col).cast(pl.Utf8).str.strip_chars(" \t\r\n")
        ])

        # Identify patient columns in methylation and expression
        meth_patient_cols = final_meth.columns[2:]
        expr_patient_cols = final_expr.columns[1:]

        # Construct phenotype rows for methylation
        meth_rows = []
        for char in selected_chars:
            row = ["", str(char)]
            for patient in meth_patient_cols:
                val = phen.filter(pl.col(id_col) == str(patient).strip())[char].to_list()
                row.append(str(val[0]) if val else "")
            meth_rows.append(row)

        expr_rows = []
        for char in selected_chars:
            row = [str(char)]
            for patient in expr_patient_cols:
                val = phen.filter(pl.col(id_col) == str(patient).strip())[char].to_list()
                row.append(str(val[0]) if val else "")
            expr_rows.append(row)

        # Ensure all values are strings
        meth_rows = [[str(cell) for cell in row] for row in meth_rows]
        expr_rows = [[str(cell) for cell in row] for row in expr_rows]

        df_new_meth = pl.DataFrame(meth_rows, schema=final_meth.columns, orient="row")
        df_new_expr = pl.DataFrame(expr_rows, schema=final_expr.columns, orient="row")

        # Cast patient columns to string before merging
        # Cast ALL columns to string to avoid dtype mismatch
        meth_cast = final_meth.select([pl.col(col).cast(pl.Utf8) for col in final_meth.columns])
        expr_cast = final_expr.select([pl.col(col).cast(pl.Utf8) for col in final_expr.columns])


        # Append phenotype rows to top of methylation and expression DataFrames
        updated_meth = pl.concat([df_new_meth, meth_cast], how="vertical")
        updated_expr = pl.concat([df_new_expr, expr_cast], how="vertical")

        self.logger.info(f"Prepended {len(selected_chars)} phenotype rows to methylation and expression files.")
        return updated_meth, updated_expr
