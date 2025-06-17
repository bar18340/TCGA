import polars as pl
from concurrent.futures import ThreadPoolExecutor
from tcga.data.file_handler import FileHandler
from tcga.data.data_phenotype import DataPhenotype
from tcga.utils.logger import setup_logger

class Controller:
    def __init__(self, logger=None):
        self.logger = logger if logger else setup_logger()
        self.file_handler = FileHandler(logger=self.logger)
        self.phenotype_processor = DataPhenotype(logger=self.logger)
    
    def process_files(self, methylation_path=None, gene_mapping_path=None, gene_expression_path=None,
                      phenotype_path=None, selected_phenotypes=None, zero_percent=0):
        """
        Handles all input file combinations (6 scenarios).
        Validates, cleans, aligns, and merges data as needed.
        """
        # Prevent invalid input combinations early
        if methylation_path and not gene_mapping_path:
            raise ValueError("Methylation file requires a corresponding gene mapping file. Please upload both.")
        if gene_mapping_path and not methylation_path:
            raise ValueError("Gene mapping file requires a corresponding methylation file. Please upload both.")

        # Upload phenotype file (optional)
        if phenotype_path:
            self.file_handler.upload_file(phenotype_path, 'phenotype')

        # Upload methylation and gene mapping files if present
        if methylation_path and gene_mapping_path:
            self.file_handler.upload_file(methylation_path, 'methylation')
            self.file_handler.upload_file(gene_mapping_path, 'gene_mapping')

        # Upload gene expression file if present
        if gene_expression_path:
            self.file_handler.upload_file(gene_expression_path, 'gene_expression')

        # Run methylation and expression cleaning in parallel if both present
        meth_result = expr_result = None
        with ThreadPoolExecutor() as executor:
            futures = []
            if methylation_path and gene_mapping_path:
                futures.append(executor.submit(self.file_handler.merge_files, zero_percent))
            if gene_expression_path:
                futures.append(executor.submit(self.file_handler.clean_gene_expression_df, zero_percent))

            results = [f.result() for f in futures]
            if len(results) == 2:
                meth_result, expr_result = results
            elif methylation_path:
                meth_result = results[0]
            else:
                expr_result = results[0]

        final_meth_df = meth_result[0] if meth_result else None
        final_expr_df = expr_result[0] if expr_result else None

        # Scenario 3: Methylation + Mapping + Expression + Phenotype
        if all([methylation_path, gene_mapping_path, gene_expression_path, phenotype_path]):
            gene_col_expr = final_expr_df.columns[0]
            common_genes = set(final_meth_df.select("Actual_Gene_Name").to_series()).intersection(
                set(final_expr_df.select(gene_col_expr).to_series()))
            if not common_genes:
                raise ValueError("No common genes found between methylation and gene expression files.")

            final_meth_df = final_meth_df.filter(pl.col("Actual_Gene_Name").is_in(common_genes))
            final_expr_df = final_expr_df.filter(pl.col(gene_col_expr).is_in(common_genes))

            meth_patients = final_meth_df.columns[2:]
            expr_patients = final_expr_df.columns[1:]
            common_patients = list(set(meth_patients).intersection(expr_patients))
            if not common_patients:
                raise ValueError("No common patient columns found.")

            final_meth_df = final_meth_df.select(["Gene_Code", "Actual_Gene_Name"] + common_patients)
            final_expr_df = final_expr_df.select([gene_col_expr] + common_patients)

            updated_meth, updated_expr = self.phenotype_processor.merge_into_files(
                final_meth_df, final_expr_df, self.file_handler.phenotype_df, selected_phenotypes)
            return updated_meth, meth_result[1] if meth_result else 0, updated_expr, expr_result[1] if expr_result else 0

        # Scenario 2.5: Methylation + Mapping + Expression (no phenotype)
        if all([methylation_path, gene_mapping_path, gene_expression_path]) and not phenotype_path:
            gene_col_expr = final_expr_df.columns[0]
            common_genes = set(final_meth_df.select("Actual_Gene_Name").to_series()).intersection(
                set(final_expr_df.select(gene_col_expr).to_series()))
            if not common_genes:
                raise ValueError("No common genes found between methylation and gene expression files.")

            final_meth_df = final_meth_df.filter(pl.col("Actual_Gene_Name").is_in(common_genes))
            final_expr_df = final_expr_df.filter(pl.col(gene_col_expr).is_in(common_genes))

            meth_patients = final_meth_df.columns[2:]
            expr_patients = final_expr_df.columns[1:]
            common_patients = list(set(meth_patients).intersection(expr_patients))
            if not common_patients:
                raise ValueError("No common patient columns found.")

            final_meth_df = final_meth_df.select(["Gene_Code", "Actual_Gene_Name"] + common_patients)
            final_expr_df = final_expr_df.select([gene_col_expr] + common_patients)

            return final_meth_df, meth_result[1], final_expr_df, expr_result[1]

        # Scenario 4: Methylation + Mapping + Phenotype (no expression)
        if all([methylation_path, gene_mapping_path, phenotype_path]) and not gene_expression_path:
            updated_meth, _ = self.phenotype_processor.merge_into_files(
                final_meth_df, final_meth_df, self.file_handler.phenotype_df, selected_phenotypes)
            return updated_meth, meth_result[1]

        # Scenario 6: Gene Expression + Phenotype
        if gene_expression_path and phenotype_path and not (methylation_path or gene_mapping_path):
            dummy_meth = pl.DataFrame(schema=["Gene_Code", "Actual_Gene_Name"])
            updated_meth, updated_expr = self.phenotype_processor.merge_into_files(
                dummy_meth, final_expr_df, self.file_handler.phenotype_df, selected_phenotypes)
            return updated_expr, expr_result[1]

        # Scenario 2: Methylation + Mapping only
        if methylation_path and gene_mapping_path and not gene_expression_path and not phenotype_path:
            return final_meth_df, meth_result[1]

        # Scenario 1: Gene Expression only
        if gene_expression_path and not (methylation_path or gene_mapping_path or phenotype_path):
            return final_expr_df, expr_result[1]

        # Catch-all for invalid combinations
        raise ValueError("Invalid file combination. Please upload a valid combination of files.")
