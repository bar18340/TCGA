import polars as pl
from polars.testing import assert_frame_equal
import pytest
from tcga.data.data_phenotype import DataPhenotype

@pytest.fixture
def phenotype_processor():
    """Provides a DataPhenotype instance for testing."""
    return DataPhenotype()

@pytest.fixture
def sample_phenotype_df():
    """A sample phenotype DataFrame. Note that Patient3 is missing."""
    return pl.DataFrame({
        "PatientID": ["Patient1", "Patient2", "Patient4"],
        "age": [50, 65, 70],
        "stage": ["Stage I", "Stage II", "Stage IV"],
    })

@pytest.fixture
def sample_methylation_df():
    """A sample final methylation DataFrame."""
    return pl.DataFrame({
        "Gene_Code": ["A", "B"],
        "Actual_Gene_Name": ["GeneA", "GeneB"],
        "Patient1": [0.1, 0.2],
        "Patient2": [0.3, 0.4],
        "Patient3": [0.5, 0.6],
    })

@pytest.fixture
def sample_expression_df():
    """A sample final gene expression DataFrame."""
    return pl.DataFrame({
        "Gene_Name": ["GeneA", "GeneC"],
        "Patient1": [100.0, 200.0],
        "Patient2": [300.0, 400.0],
        "Patient3": [500.0, 600.0],
    })


def test_get_characteristics(phenotype_processor, sample_phenotype_df):
    """
    Tests that the correct list of characteristic names is returned.
    """
    characteristics = phenotype_processor.get_characteristics(sample_phenotype_df)
    assert characteristics == ["age", "stage"]

def test_merge_into_files(phenotype_processor, sample_methylation_df, sample_expression_df, sample_phenotype_df):
    """
    Tests the main scenario where phenotype rows are added to both methylation and expression files.
    """
    selected_chars = ["age", "stage"]
    
    expected_meth = pl.DataFrame({
        "Gene_Code": ["", ""],
        "Actual_Gene_Name": ["age", "stage"],
        "Patient1": ["50", "Stage I"],
        "Patient2": ["65", "Stage II"],
        "Patient3": ["", ""],
    }).vstack(sample_methylation_df.cast(pl.Utf8))

    expected_expr = pl.DataFrame({
        "Gene_Name": ["age", "stage"],
        "Patient1": ["50", "Stage I"],
        "Patient2": ["65", "Stage II"],
        "Patient3": ["", ""],
    }).vstack(sample_expression_df.cast(pl.Utf8))

    updated_meth, updated_expr = phenotype_processor.merge_into_files(
        sample_methylation_df, sample_expression_df, sample_phenotype_df, selected_chars
    )

    assert_frame_equal(updated_meth, expected_meth)
    assert_frame_equal(updated_expr, expected_expr)

def test_merge_into_files_only_methylation(phenotype_processor, sample_methylation_df, sample_phenotype_df):
    """
    Tests that phenotype merging works correctly when only a methylation file is provided.
    """
    selected_chars = ["age"]
    
    expected_meth = pl.DataFrame({
        "Gene_Code": [""],
        "Actual_Gene_Name": ["age"],
        "Patient1": ["50"],
        "Patient2": ["65"],
        "Patient3": [""],
    }).vstack(sample_methylation_df.cast(pl.Utf8)) 

    updated_meth, updated_expr = phenotype_processor.merge_into_files(
        sample_methylation_df, None, sample_phenotype_df, selected_chars
    )

    assert updated_expr is None
    assert_frame_equal(updated_meth, expected_meth)

def test_merge_returns_unmodified_if_no_phenotypes_selected(phenotype_processor, sample_methylation_df, sample_expression_df, sample_phenotype_df):
    """
    Tests that the original DataFrames are returned if the list of selected phenotypes is empty.
    """
    selected_chars = []
    updated_meth, updated_expr = phenotype_processor.merge_into_files(
        sample_methylation_df, sample_expression_df, sample_phenotype_df, selected_chars
    )
    assert_frame_equal(updated_meth, sample_methylation_df)
    assert_frame_equal(updated_expr, sample_expression_df)