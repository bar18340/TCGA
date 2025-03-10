import pandas as pd
from tcga.data.file_handler import FileHandler
from tcga.data.data_phenotype import DataPhenotype
from tcga.utils.logger import setup_logger

class Controller:
    def __init__(self, logger=None):
        """
        Initializes the Controller with a FileHandler instance.
        """
        self.logger = logger if logger else setup_logger()
        self.file_handler = FileHandler(logger=self.logger)
        self.phenotype_processor = DataPhenotype(logger=self.logger)

    def process_files(self, methylation_path=None, gene_mapping_path=None, gene_expression_path=None,
                      phenotype_path=None, selected_phenotypes=None, zero_percent=0):
        """
        Processes files based on the following scenarios:
        
          1. Only Gene Expression File.
          2. Methylation + Gene Mapping Files.
          3. Methylation + Gene Mapping + Gene Expression.
          4. Methylation + Gene Mapping + Phenotype.
          5. Gene Expression + Phenotype.
          6. Methylation + Gene Mapping + Gene Expression + Phenotype.
        
        If a phenotype file is provided, it is uploaded and its selected characteristics
        are merged into the final output(s) by adding new rows at the top.
        
        Returns:
          - Scenario 1: (cleaned_gene_expression_df, rows_removed_expr)
          - Scenario 2: (cleaned_methylation_df, rows_removed_methylation)
          - Scenario 3: (final_methylation_df, rows_removed_methylation, final_gene_expression_df, rows_removed_expr)
          - Scenario 4: (final_methylation_df, rows_removed_methylation)
          - Scenario 5: (final_gene_expression_df, rows_removed_expr)
          - Scenario 6: (final_methylation_df, rows_removed_methylation, final_gene_expression_df, rows_removed_expr)
        """
        try:
            # Upload phenotype file if provided
            if phenotype_path:
                self.file_handler.upload_file(phenotype_path, 'phenotype')

            # Scenario 6: All Three Files + Phenotype
            if methylation_path and gene_mapping_path and gene_expression_path and phenotype_path:
                self.logger.info("Processing Scenario 6: All three files with phenotype.")
                self.file_handler.upload_file(methylation_path, 'methylation')
                self.file_handler.upload_file(gene_mapping_path, 'gene_mapping')
                self.file_handler.upload_file(gene_expression_path, 'gene_expression')
                cleaned_meth_df, rows_removed_meth = self.file_handler.merge_files(zero_percent=zero_percent)
                cleaned_expr_df, rows_removed_expr = self.file_handler.clean_gene_expression_df(zero_percent=zero_percent)
                common_genes = set(cleaned_meth_df.iloc[:, 1]).intersection(set(cleaned_expr_df.iloc[:, 0]))
                self.logger.debug(f"Found {len(common_genes)} common genes based on gene identifiers.")
                if not common_genes:
                    raise ValueError("No common genes found between methylation and gene expression files.")
                filtered_meth = cleaned_meth_df[cleaned_meth_df.iloc[:, 1].isin(common_genes)].copy()
                filtered_expr = cleaned_expr_df[cleaned_expr_df.iloc[:, 0].isin(common_genes)].copy()
                meth_patients = list(cleaned_meth_df.columns[2:])
                expr_patients = list(cleaned_expr_df.columns[1:])
                self.logger.debug(f"Methylation patient headers: {meth_patients}")
                self.logger.debug(f"Gene expression patient headers: {expr_patients}")
                common_patients = [col for col in meth_patients if col in expr_patients]
                self.logger.debug(f"Common patient columns: {common_patients}")
                if not common_patients:
                    raise ValueError("No common patient columns found between methylation and gene expression files.")
                final_meth = filtered_meth[[filtered_meth.columns[0], filtered_meth.columns[1]] + common_patients]
                final_expr = filtered_expr[[filtered_expr.columns[0]] + common_patients]
                final_meth, final_expr = self.phenotype_processor.merge_into_files(final_meth, final_expr, self.file_handler.phenotype_df, selected_phenotypes)
                return final_meth, rows_removed_meth, final_expr, rows_removed_expr

            # Scenario 5: Gene Expression + Phenotype
            elif gene_expression_path and not (methylation_path or gene_mapping_path) and phenotype_path:
                self.logger.info("Processing Scenario 5: Gene Expression + Phenotype.")
                self.file_handler.upload_file(gene_expression_path, 'gene_expression')
                cleaned_expr_df, rows_removed_expr = self.file_handler.clean_gene_expression_df(zero_percent=zero_percent)
                final_expr = cleaned_expr_df.copy()
                # Merge phenotype rows into gene expression file
                _, final_expr = self.phenotype_processor.merge_into_files(final_expr, final_expr, self.file_handler.phenotype_df, selected_phenotypes)
                return final_expr, rows_removed_expr

            # Scenario 4: Methylation + Gene Mapping + Phenotype
            elif methylation_path and gene_mapping_path and not gene_expression_path and phenotype_path:
                self.logger.info("Processing Scenario 4: Methylation + Gene Mapping + Phenotype.")
                self.file_handler.upload_file(methylation_path, 'methylation')
                self.file_handler.upload_file(gene_mapping_path, 'gene_mapping')
                cleaned_meth_df, rows_removed_meth = self.file_handler.merge_files(zero_percent=zero_percent)
                final_meth, _ = self.phenotype_processor.merge_into_files(cleaned_meth_df, cleaned_meth_df, self.file_handler.phenotype_df, selected_phenotypes)
                return final_meth, rows_removed_meth

            # Scenario 3: Methylation + Gene Mapping + Gene Expression (no phenotype)
            elif methylation_path and gene_mapping_path and gene_expression_path and not phenotype_path:
                self.logger.info("Processing Scenario 3: Methylation, Gene Mapping, and Gene Expression (no phenotype).")
                self.file_handler.upload_file(methylation_path, 'methylation')
                self.file_handler.upload_file(gene_mapping_path, 'gene_mapping')
                self.file_handler.upload_file(gene_expression_path, 'gene_expression')
                cleaned_meth_df, rows_removed_meth = self.file_handler.merge_files(zero_percent=zero_percent)
                cleaned_expr_df, rows_removed_expr = self.file_handler.clean_gene_expression_df(zero_percent=zero_percent)
                common_genes = set(cleaned_meth_df.iloc[:, 1]).intersection(set(cleaned_expr_df.iloc[:, 0]))
                self.logger.debug(f"Found {len(common_genes)} common genes based on gene identifiers.")
                if not common_genes:
                    raise ValueError("No common genes found between methylation and gene expression files.")
                filtered_meth = cleaned_meth_df[cleaned_meth_df.iloc[:, 1].isin(common_genes)].copy()
                filtered_expr = cleaned_expr_df[cleaned_expr_df.iloc[:, 0].isin(common_genes)].copy()
                meth_patients = list(cleaned_meth_df.columns[2:])
                expr_patients = list(cleaned_expr_df.columns[1:])
                self.logger.debug(f"Methylation patient headers: {meth_patients}")
                self.logger.debug(f"Gene expression patient headers: {expr_patients}")
                common_patients = [col for col in meth_patients if col in expr_patients]
                self.logger.debug(f"Common patient columns: {common_patients}")
                if not common_patients:
                    raise ValueError("No common patient columns found between methylation and gene expression files.")
                final_meth = filtered_meth[[filtered_meth.columns[0], filtered_meth.columns[1]] + common_patients]
                final_expr = filtered_expr[[filtered_expr.columns[0]] + common_patients]
                return final_meth, rows_removed_meth, final_expr, rows_removed_expr

            # Scenario 2: Only Methylation + Gene Mapping Files (no phenotype)
            elif methylation_path and gene_mapping_path and not gene_expression_path and not phenotype_path:
                self.logger.info("Processing Scenario 2: Methylation + Gene Mapping Files (no phenotype).")
                self.file_handler.upload_file(methylation_path, 'methylation')
                self.file_handler.upload_file(gene_mapping_path, 'gene_mapping')
                cleaned_meth_df, rows_removed_meth = self.file_handler.merge_files(zero_percent=zero_percent)
                return cleaned_meth_df, rows_removed_meth

            # Scenario 1: Only Gene Expression File (no phenotype)
            elif gene_expression_path and not (methylation_path or gene_mapping_path) and not phenotype_path:
                self.logger.info("Processing Scenario 1: Only Gene Expression File (no phenotype).")
                self.file_handler.upload_file(gene_expression_path, 'gene_expression')
                cleaned_expr_df, rows_removed_expr = self.file_handler.clean_gene_expression_df(zero_percent=zero_percent)
                return cleaned_expr_df, rows_removed_expr

            else:
                raise ValueError("Invalid combination of files. Please upload either only gene expression, or methylation with gene mapping, or all three files (optionally with phenotype).")
        except Exception as e:
            self.logger.error(f"Error processing files: {e}", exc_info=True)
            raise e
