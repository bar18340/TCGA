import pandas as pd
from tcga.utils.logger import setup_logger

class DataPhenotype:
    def __init__(self, logger=None):
        self.logger = logger if logger else setup_logger()

    def get_characteristics(self, phenotype_df: pd.DataFrame) -> list:
        """
        Returns a list of phenotype characteristics (all header names except the first column).
        """
        # Skip the first column (patient IDs)
        characteristics = list(phenotype_df.columns[1:])
        self.logger.debug(f"Extracted phenotype characteristics: {characteristics}")
        return characteristics

    def merge_into_files(self, final_meth: pd.DataFrame, final_expr: pd.DataFrame,
                           phenotype_df: pd.DataFrame, selected_chars: list) -> tuple:
        """
        For each selected phenotype characteristic, adds a new row at the top of both final_meth and final_expr.
        
        - For methylation: New row has first cell empty, second cell the phenotype name,
          and subsequent cells filled with the phenotype value (matched by patient).
        - For gene expression: New row has first cell set to the phenotype name and the remaining cells the phenotype values.
        
        Patient matching is performed by comparing patient IDs from the phenotype file (first column)
        with the headers:
          • In final_meth, patients are in columns from index 2 onward.
          • In final_expr, patients are in columns from index 1 onward.
        """
        # Make a copy and ensure patient IDs are strings and stripped
        phenotype_df = phenotype_df.copy()
        phenotype_df.iloc[:, 0] = phenotype_df.iloc[:, 0].astype(str).str.strip()
        # Build a dictionary keyed by patient ID with their phenotype data
        phen_dict = phenotype_df.set_index(phenotype_df.columns[0]).to_dict('index')

        # Get patient headers from the final outputs
        meth_patients = list(final_meth.columns[2:])  # from third column onward
        expr_patients = list(final_expr.columns[1:])    # from second column onward

        new_rows_meth = []
        new_rows_expr = []
        for char in selected_chars:
            # For methylation: new row with empty first cell, second cell is characteristic name
            row_meth = ["", char]
            for patient in meth_patients:
                patient_val = phen_dict.get(str(patient).strip(), {}).get(char, "")
                row_meth.append(patient_val)
            new_rows_meth.append(row_meth)
            
            # For gene expression: new row with first cell is characteristic name
            row_expr = [char]
            for patient in expr_patients:
                patient_val = phen_dict.get(str(patient).strip(), {}).get(char, "")
                row_expr.append(patient_val)
            new_rows_expr.append(row_expr)

        # Create DataFrames for the new rows (using the same columns as the final outputs)
        df_new_meth = pd.DataFrame(new_rows_meth, columns=final_meth.columns)
        df_new_expr = pd.DataFrame(new_rows_expr, columns=final_expr.columns)

        self.logger.info(f"Created {len(selected_chars)} phenotype rows.")
        # Prepend the new rows to the final DataFrames
        updated_meth = pd.concat([df_new_meth, final_meth], ignore_index=True)
        updated_expr = pd.concat([df_new_expr, final_expr], ignore_index=True)
        return updated_meth, updated_expr
