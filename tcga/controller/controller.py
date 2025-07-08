import polars as pl
from tcga.data.file_handler import FileHandler
from tcga.data.data_phenotype import DataPhenotype
from tcga.data.data_merger import DataMerger
from tcga.data.data_cleaner import DataCleaner
from tcga.utils.logger import setup_logger

class Controller:
    """
    Main controller for orchestrating TCGA data processing.
    """

    def __init__(self, logger=None):
        self.logger = logger if logger else setup_logger()
        self.file_handler = FileHandler(logger=self.logger)
        self.data_merger = DataMerger(logger=self.logger)
        self.data_cleaner = DataCleaner(logger=self.logger)
        self.phenotype_processor = DataPhenotype(logger=self.logger)
    
    def process_files(self, methylation_path=None, gene_mapping_path=None, gene_expression_path=None,
                      phenotype_path=None, selected_phenotypes=None, zero_percent=100.0):
        """
        Handles all input file combinations by orchestrating the processing workflow.
        """        
        # 1. Load data from files and perform initial validation
        meth_df, map_df, expr_df, pheno_df = self._load_and_validate_files(
            methylation_path, gene_mapping_path, gene_expression_path, phenotype_path
        )

        # 2. Perform initial cleaning (NA values, invalid gene names)
        cleaned_meth, cleaned_expr = self._perform_initial_cleaning(meth_df, map_df, expr_df)

        # 3. Find common genes and patients
        aligned_meth, aligned_expr = self._intersect_dataframes(cleaned_meth, cleaned_expr, meth_df, expr_df)

        # 4. Apply the zero-percentage filter on the aligned data
        filtered_meth, filtered_expr = self._apply_zero_filters(aligned_meth, aligned_expr, zero_percent)

        # 5. Re-align the data after filtering to ensure it's still mutual
        final_meth, final_expr = self._realign_after_filtering(filtered_meth, filtered_expr)

        # 6. Add phenotype data to the final, processed files
        final_meth, final_expr = self._add_phenotype_data(
            final_meth, final_expr, pheno_df, selected_phenotypes
        )
            
        return final_meth, final_expr

    # Private Helper Methods for Each Step

    def _load_and_validate_files(self, methylation_path, gene_mapping_path, gene_expression_path, phenotype_path):
        """Loads all provided files and validates required combinations."""
        meth_df = self.file_handler.load_dataframe(methylation_path, 'methylation')
        map_df = self.file_handler.load_dataframe(gene_mapping_path, 'gene_mapping')
        expr_df = self.file_handler.load_dataframe(gene_expression_path, 'gene_expression')
        pheno_df = self.file_handler.load_dataframe(phenotype_path, 'phenotype')

        if meth_df is not None and map_df is None:
            raise ValueError("Methylation file was provided without a gene mapping file.")
        if map_df is not None and meth_df is None:
            raise ValueError("Gene mapping file was provided without a methylation file.")
        
        return meth_df, map_df, expr_df, pheno_df

    def _perform_initial_cleaning(self, meth_df, map_df, expr_df):
        """Performs initial data cleaning (NA, invalid values)."""
        cleaned_meth = None
        if meth_df is not None and map_df is not None:
            merged_df = self.data_merger.merge(meth_df, map_df)
            cleaned_meth = self.data_cleaner.clean_merged_df(merged_df)
        
        # Currently, the expression file has no initial cleaning step, but this
        # structure allows one to be easily added in the future.
        cleaned_expr = expr_df if expr_df is not None else None
        
        return cleaned_meth, cleaned_expr

    def _intersect_dataframes(self, meth_df, expr_df, original_meth_df, original_expr_df):
        """Finds and filters by common genes and patients."""
        if meth_df is None or expr_df is None:
            return meth_df, expr_df

        self.logger.info("Aligning files to common genes and patients.")
        # 1. Get a unique set of all gene names from the expression file.
        expr_gene_set = set(expr_df.get_column("Gene_Name").to_list())
        
        # 2. For each row in the methylation file, check if ANY of its comma-separated
        #    gene names exist in the expression gene set.
        match_mask = meth_df.get_column("Actual_Gene_Name").map_elements(
            lambda name_str: any(name in expr_gene_set for name in name_str.split(",")) if name_str else False,
            return_dtype=pl.Boolean
        )
        
        # 3. Filter the methylation file to keep only the rows that had at least one match.
        meth_df = meth_df.filter(match_mask)
        
        # 4. Create a set of all valid gene names from the filtered methylation file.
        valid_meth_genes = meth_df.select(
            pl.col("Actual_Gene_Name").str.split(",")
        ).explode("Actual_Gene_Name").unique().to_series().to_list()
        
        # 5. Filter the expression file to keep only the genes that are part of the valid set.
        expr_df = expr_df.filter(pl.col("Gene_Name").is_in(list(valid_meth_genes)))

        if meth_df.is_empty() or expr_df.is_empty():
            raise ValueError("No common genes found between methylation and expression files.")
        
        # Patient intersection logic
        original_meth_patients = original_meth_df.columns[1:]
        expr_patients_set = set(original_expr_df.columns[1:])
        common_patients = [p for p in original_meth_patients if p in expr_patients_set]
        
        if not common_patients:
            raise ValueError("No common patient columns found.")

        meth_df = meth_df.select(["Gene_Code", "Actual_Gene_Name"] + common_patients)
        expr_df = expr_df.select(["Gene_Name"] + common_patients)
        
        return meth_df, expr_df

    def _apply_zero_filters(self, meth_df, expr_df, zero_percent):
        """Applies the zero-percentage filter to both dataframes."""
        if meth_df is not None:
            meth_df = self.data_cleaner.filter_by_zero_percentage(
                meth_df, zero_percent, id_cols=["Gene_Code", "Actual_Gene_Name"]
            )
        if expr_df is not None:
            expr_df = self.data_cleaner.filter_by_zero_percentage(
                expr_df, zero_percent, id_cols=["Gene_Name"]
            )
        return meth_df, expr_df
    
    def _realign_after_filtering(self, meth_df, expr_df):
        """Re-intersects genes after zero-filtering to ensure alignment."""
        if meth_df is None or expr_df is None:
            return meth_df, expr_df
            
        self.logger.info("Re-aligning genes after zero-filtering to ensure consistency.")
        expr_gene_set = set(expr_df.get_column("Gene_Name").to_list())
        match_mask = meth_df.get_column("Actual_Gene_Name").map_elements(
            lambda s: any(g in expr_gene_set for g in s.split(",")) if s else False,
            return_dtype=pl.Boolean
        )
        meth_df = meth_df.filter(match_mask)
        valid_meth_genes = meth_df.select(
            pl.col("Actual_Gene_Name").str.split(",")
        ).explode("Actual_Gene_Name").unique().to_series().to_list()
        expr_df = expr_df.filter(pl.col("Gene_Name").is_in(list(valid_meth_genes)))
        return meth_df, expr_df
    
    def _add_phenotype_data(self, meth_df, expr_df, pheno_df, selected_phenotypes):
        """Adds phenotype rows to the final dataframes."""
        if pheno_df is not None and selected_phenotypes:
            meth_df, expr_df = self.phenotype_processor.merge_into_files(
                meth_df, expr_df, pheno_df, selected_phenotypes
            )
        return meth_df, expr_df