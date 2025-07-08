import polars as pl
from tcga.utils.logger import setup_logger

class DataPhenotype:
    """
    Provides utilities for handling phenotype data in TCGA workflows.

    This class allows extraction of phenotype characteristics (columns) and merging phenotype information
    into methylation and gene expression DataFrames as additional rows for downstream analysis.

    Notes:
    - The first column of the phenotype file is assumed to be patient IDs.
    - All phenotype values are prepended as rows (not columns) to the output files, matching patient columns by ID.
    - Missing phenotype values for a patient are represented as empty strings.
    - All output values are cast to string to avoid dtype mismatches during concatenation.
    """
    def __init__(self, logger=None):
        """
        Initializes the DataPhenotype instance.
        """
        self.logger = logger if logger else setup_logger()

    def get_characteristics(self, phenotype_df: pl.DataFrame) -> list:
        """
        Returns all phenotype characteristics except the first column (patient IDs).

        Args:
            phenotype_df (pl.DataFrame): The phenotype DataFrame.

        Returns:
            list: List of phenotype characteristic column names (excluding patient ID).
        """
        if phenotype_df.is_empty() or phenotype_df.shape[1] < 2:
            return []
        return phenotype_df.columns[1:]

    def merge_into_files(self, final_meth_df: pl.DataFrame, final_expr_df: pl.DataFrame,
                         phenotype_df: pl.DataFrame, selected_chars: list) -> tuple:
        """
        Adds rows for selected phenotype characteristics to both methylation and expression files.

        Each row contains a characteristic and its values for matching patients.
        Missing values are left as empty strings.

        Args:
            final_meth (pl.DataFrame): The final methylation DataFrame (patients as columns).
            final_expr (pl.DataFrame): The final gene expression DataFrame (patients as columns).
            phenotype_df (pl.DataFrame): The phenotype DataFrame.
            selected_chars (list): List of phenotype characteristics to add.

        Returns:
            tuple: (updated_meth, updated_expr) where both are polars DataFrames with phenotype rows prepended.

        Notes:
        - Patient columns in methylation start from index 2 (after 'Gene_Code', 'Actual_Gene_Name').
        - Patient columns in expression start from index 1 (after 'Gene_Name').
        - All columns are cast to string before concatenation to avoid dtype errors.
        """
        if not selected_chars or phenotype_df is None:
            return final_meth_df, final_expr_df

        id_col = phenotype_df.columns[0]
        
        # Prepare phenotype lookup by converting patient IDs to a dictionary for fast access
        phenotype_lookup = phenotype_df.select([id_col] + selected_chars).to_dicts()
        pheno_map = {str(row[id_col]).strip(): row for row in phenotype_lookup}

        # Process Methylation File
        if final_meth_df is not None:
            meth_patient_cols = final_meth_df.columns[2:]
            meth_rows = []
            for char in selected_chars:
                row_data = {"Gene_Code": "", "Actual_Gene_Name": char}
                for patient in meth_patient_cols:
                    patient_id = str(patient).strip()
                    # Look up patient in the map. provide empty string if not found or value is None
                    patient_pheno = pheno_map.get(patient_id, {})
                    row_data[patient] = str(patient_pheno.get(char, "") or "")
                meth_rows.append(row_data)

            df_new_meth = pl.DataFrame(meth_rows)
            # Ensure column order matches before concatenation
            df_new_meth = df_new_meth.select(final_meth_df.columns)
            final_meth_df = pl.concat([df_new_meth, final_meth_df.cast(pl.Utf8)], how="vertical")
            self.logger.info(f"Added {len(selected_chars)} phenotype rows to methylation data.")

        # Process Expression File
        if final_expr_df is not None:
            expr_gene_col = final_expr_df.columns[0]
            expr_patient_cols = final_expr_df.columns[1:]
            expr_rows = []
            for char in selected_chars:
                row_data = {expr_gene_col: char}
                for patient in expr_patient_cols:
                    patient_id = str(patient).strip()
                    patient_pheno = pheno_map.get(patient_id, {})
                    row_data[patient] = str(patient_pheno.get(char, "") or "")
                expr_rows.append(row_data)

            df_new_expr = pl.DataFrame(expr_rows)
            df_new_expr = df_new_expr.select(final_expr_df.columns)
            final_expr_df = pl.concat([df_new_expr, final_expr_df.cast(pl.Utf8)], how="vertical")
            self.logger.info(f"Added {len(selected_chars)} phenotype rows to expression data.")
            
        return final_meth_df, final_expr_df
