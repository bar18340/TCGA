# tcga/controller/controller.py

import pandas as pd
from tcga.data.file_handler import FileHandler
from tcga.utils.logger import setup_logger

class Controller:
    def __init__(self, logger=None):
        """
        Initializes the Controller with a FileHandler instance.
        """
        self.logger = logger if logger else setup_logger()
        self.file_handler = FileHandler(logger=self.logger)

    def process_files(self, methylation_path=None, gene_mapping_path=None, gene_expression_path=None, zero_percent=0):
        """
        Handles the process of uploading and processing files.
        Supports three scenarios:
          1. Only Gene Expression File.
          2. Methylation + Gene Mapping Files.
          3. All Three Files.
        
        Returns:
          - Scenario 1: (cleaned_gene_expression_df, rows_removed_gene_expression)
          - Scenario 2: (cleaned_methylation_df, rows_removed_methylation)
          - Scenario 3: (final_methylation_df, rows_removed_methylation, final_gene_expression_df, rows_removed_gene_expression)
        """
        try:
            # Scenario 3: All Three Files
            if methylation_path and gene_mapping_path and gene_expression_path:
                self.logger.info("Processing Scenario 3: All Three Files.")
                self.file_handler.upload_file(methylation_path, 'methylation')
                self.file_handler.upload_file(gene_mapping_path, 'gene_mapping')
                self.file_handler.upload_file(gene_expression_path, 'gene_expression')

                # Clean methylation and gene expression files separately
                cleaned_meth_df, rows_removed_meth = self.file_handler.merge_files(zero_percent=zero_percent)
                cleaned_expr_df, rows_removed_expr = self.file_handler.clean_gene_expression_df(zero_percent=zero_percent)

                # Compare gene names:
                # For methylation, actual gene names are in the second column (index 1)
                # For gene expression, gene names are in the first column (index 0)
                common_genes = set(cleaned_meth_df.iloc[:, 1]).intersection(set(cleaned_expr_df.iloc[:, 0]))
                self.logger.debug(f"Found {len(common_genes)} common genes based on gene identifiers.")
                if not common_genes:
                    raise ValueError("No common genes found between methylation and gene expression files.")

                # Filter rows based on common genes using column positions:
                filtered_meth = cleaned_meth_df[cleaned_meth_df.iloc[:, 1].isin(common_genes)].copy()
                filtered_expr = cleaned_expr_df[cleaned_expr_df.iloc[:, 0].isin(common_genes)].copy()

                # For patient/sample columns:
                # In methylation, patients are in the header starting from the third column (index 2)
                # In gene expression, patients are in the header starting from the second column (index 1)
                meth_patients = list(cleaned_meth_df.columns[2:])
                expr_patients = list(cleaned_expr_df.columns[1:])
                self.logger.debug(f"Methylation patient headers: {meth_patients}")
                self.logger.debug(f"Gene expression patient headers: {expr_patients}")

                # Determine the common patient headers (by name)
                common_patients = [col for col in meth_patients if col in expr_patients]
                self.logger.debug(f"Common patient columns based on header names: {common_patients}")
                if not common_patients:
                    raise ValueError("No common patient columns found between methylation and gene expression files.")

                # Build final DataFrames:
                # For methylation: keep first two columns plus common patient columns
                final_meth = filtered_meth[[filtered_meth.columns[0], filtered_meth.columns[1]] + common_patients]
                # For gene expression: keep the first column plus common patient columns
                final_expr = filtered_expr[[filtered_expr.columns[0]] + common_patients]

                return final_meth, rows_removed_meth, final_expr, rows_removed_expr


            # Scenario 2: Only Methylation + Gene Mapping Files
            elif methylation_path and gene_mapping_path and not gene_expression_path:
                self.logger.info("Processing Scenario 2: Methylation + Gene Mapping Files.")
                self.file_handler.upload_file(methylation_path, 'methylation')
                self.file_handler.upload_file(gene_mapping_path, 'gene_mapping')
                cleaned_meth_df, rows_removed_meth = self.file_handler.merge_files(zero_percent=zero_percent)
                return cleaned_meth_df, rows_removed_meth

            # Scenario 1: Only Gene Expression File
            elif gene_expression_path and not (methylation_path or gene_mapping_path):
                self.logger.info("Processing Scenario 1: Only Gene Expression File.")
                self.file_handler.upload_file(gene_expression_path, 'gene_expression')
                cleaned_expr_df, rows_removed_expr = self.file_handler.clean_gene_expression_df(zero_percent=zero_percent)
                return cleaned_expr_df, rows_removed_expr

            else:
                raise ValueError("Invalid combination of files. Please upload either only gene expression, or methylation with gene mapping, or all three files.")
        except Exception as e:
            self.logger.error(f"Error processing files: {e}", exc_info=True)
            raise e
