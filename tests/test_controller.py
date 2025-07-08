import polars as pl
from polars.testing import assert_frame_equal
import pytest
from tcga.controller.controller import Controller


@pytest.fixture
def sample_methylation_df():
    return pl.DataFrame({
        "Gene_Code": ["cg01", "cg02", "cg03"], 
        "PatientA": [0.1, 0.2, 0.3], 
        "PatientB": [0.4, 0.5, 0.6]
    })

@pytest.fixture
def sample_gene_mapping_df():
    return pl.DataFrame({
        "Gene_Code": ["cg01", "cg02", "cg03"], 
        "Actual_Gene_Name": ["GENE_A", "GENE_B", "."]
    })

@pytest.fixture
def sample_expression_df():
    return pl.DataFrame({
        "Gene_Name": ["GENE_A", "GENE_B", "GENE_C"], 
        "PatientA": [10, 20, 30], 
        "PatientB": [40, 50, 60], 
        "PatientC": [70, 80, 90]
    })

@pytest.fixture
def sample_phenotype_df():
    return pl.DataFrame({
        "PatientID": ["PatientA", "PatientC"], 
        "age": [50, 65], 
        "stage": ["I", "II"]
    })

@pytest.fixture
def controller():
    """Provides a Controller instance for testing."""
    return Controller()

def test_scenario_methylation_and_mapping_only(mocker, controller, sample_methylation_df, sample_gene_mapping_df):
    mocker.patch('tcga.data.file_handler.FileHandler.load_dataframe', side_effect=[
        sample_methylation_df, sample_gene_mapping_df, None, None
    ])
    final_meth, final_expr = controller.process_files(
        methylation_path="fake/meth.txt", gene_mapping_path="fake/map.txt"
    )
    assert final_expr is None
    assert final_meth is not None
    assert final_meth.shape[0] == 2

def test_scenario_expression_only(mocker, controller, sample_expression_df):
    mocker.patch('tcga.data.file_handler.FileHandler.load_dataframe', side_effect=[
        None, None, sample_expression_df, None
    ])
    final_meth, final_expr = controller.process_files(gene_expression_path="fake/expr.txt")
    assert final_meth is None
    assert final_expr is not None
    assert_frame_equal(final_expr, sample_expression_df)

def test_scenario_meth_and_expr_no_pheno(mocker, controller, sample_methylation_df, sample_gene_mapping_df, sample_expression_df):
    mocker.patch('tcga.data.file_handler.FileHandler.load_dataframe', side_effect=[
        sample_methylation_df, sample_gene_mapping_df, sample_expression_df, None
    ])
    final_meth, final_expr = controller.process_files(
        methylation_path="fake/meth.txt", gene_mapping_path="fake/map.txt", gene_expression_path="fake/expr.txt"
    )
    assert final_meth.shape[0] == 2
    assert final_expr.shape[0] == 2

def test_scenario_all_files(mocker, controller, sample_methylation_df, sample_gene_mapping_df, sample_expression_df, sample_phenotype_df):
    mocker.patch('tcga.data.file_handler.FileHandler.load_dataframe', side_effect=[
        sample_methylation_df, sample_gene_mapping_df, sample_expression_df, sample_phenotype_df
    ])
    final_meth, final_expr = controller.process_files(
        methylation_path="fake/meth.txt", gene_mapping_path="fake/map.txt",
        gene_expression_path="fake/expr.txt", phenotype_path="fake/pheno.txt",
        selected_phenotypes=["age"]
    )
    assert final_meth.shape[0] == 3
    assert final_expr.shape[0] == 3

def test_error_missing_mapping_file(mocker, controller, sample_methylation_df):
    mocker.patch('tcga.data.file_handler.FileHandler.load_dataframe', side_effect=[
        sample_methylation_df, None, None, None
    ])
    with pytest.raises(ValueError, match="Methylation file was provided without a gene mapping file."):
        controller.process_files(methylation_path="fake/meth.txt")

def test_error_no_common_genes(mocker, controller, sample_methylation_df, sample_expression_df):
    no_common_gene_map = pl.DataFrame({"Gene_Code": ["cg01"], "Actual_Gene_Name": ["GENE_Z"]})
    mocker.patch('tcga.data.file_handler.FileHandler.load_dataframe', side_effect=[
        sample_methylation_df, no_common_gene_map, sample_expression_df, None
    ])
    with pytest.raises(ValueError, match="No common genes found"):
        controller.process_files(
            methylation_path="fake/meth.txt", gene_mapping_path="fake/map.txt", gene_expression_path="fake/expr.txt"
        )