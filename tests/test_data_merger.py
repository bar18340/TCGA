import polars as pl
from polars.testing import assert_frame_equal
import pytest
from tcga.data.data_merger import DataMerger

@pytest.fixture
def data_merger():
    return DataMerger()

@pytest.fixture
def sample_methylation_df():
    return pl.DataFrame({
        "Gene_Code": ["A", "B", "C"],
        "Patient1": [0.1, 0.2, 0.3],
        "Patient2": [0.4, 0.5, 0.6],
    })

@pytest.fixture
def sample_gene_mapping_df():
    return pl.DataFrame({
        "Gene_Code": ["A", "B", "D"],
        "Actual_Gene_Name": ["Gene_A_Real", "Gene_B_Real", "Gene_D_Real"],
    })

def test_successful_merge(data_merger, sample_methylation_df, sample_gene_mapping_df):
    """
    Tests a successful inner join operation.
    """
    expected_df = pl.DataFrame({
        "Gene_Code": ["A", "B"],
        "Actual_Gene_Name": ["Gene_A_Real", "Gene_B_Real"],
        "Patient1": [0.1, 0.2],
        "Patient2": [0.4, 0.5],
    })

    merged_df = data_merger.merge(sample_methylation_df, sample_gene_mapping_df)

    expected_df = expected_df.select([
        pl.col("Gene_Code").cast(pl.Utf8), pl.col("Actual_Gene_Name").cast(pl.Utf8),
        pl.col("Patient1").cast(pl.Float64), pl.col("Patient2").cast(pl.Float64)
    ])
    assert_frame_equal(merged_df, expected_df)

def test_merge_raises_error_if_gene_code_missing(data_merger, sample_methylation_df):
    """
    Confirms that the process will fail with a specific error if either of the input files is missing the required Gene_Code column.
    """
    invalid_mapping_df = pl.DataFrame({"Wrong_Column": ["A"], "Name": ["GeneA"]})
    with pytest.raises(ValueError, match="must contain a 'Gene_Code' column"):
        data_merger.merge(sample_methylation_df, invalid_mapping_df)

def test_merge_raises_error_on_duplicate_gene_codes(data_merger, sample_methylation_df):
    """
    Ensures the application stops with an error if the gene mapping file contains duplicate Gene_Code entries.
    """
    duplicate_mapping_df = pl.DataFrame({
        "Gene_Code": ["A", "A", "B"], "Actual_Gene_Name": ["G1", "G2", "G3"]
    })
    with pytest.raises(ValueError, match="contains duplicate Gene_Code entries"):
        data_merger.merge(sample_methylation_df, duplicate_mapping_df)

def test_column_reordering(data_merger):
    """
    Checks that after a successful merge, the columns are always reordered to place Gene_Code and Actual_Gene_Name as the first two columns for consistency.
    """
    methylation_df = pl.DataFrame({"Patient1": [0.1], "Gene_Code": ["A"]})
    gene_mapping_df = pl.DataFrame({"Actual_Gene_Name": ["RealA"], "Gene_Code": ["A"]})
    merged_df = data_merger.merge(methylation_df, gene_mapping_df)
    expected_columns = ["Gene_Code", "Actual_Gene_Name", "Patient1"]
    assert merged_df.columns == expected_columns

def test_merge_with_empty_dataframes(data_merger):
    """Test merging when one or both dataframes are empty."""
    # Create empty dataframe with explicit schema
    empty_df = pl.DataFrame(
        {"Gene_Code": [], "Actual_Gene_Name": []},
        schema={"Gene_Code": pl.Utf8, "Actual_Gene_Name": pl.Utf8}
    )
    normal_df = pl.DataFrame({"Gene_Code": ["A"], "Patient1": [0.1]})
    
    result = data_merger.merge(normal_df, empty_df)
    assert result.shape[0] == 0  # Inner join should result in empty

def test_merge_with_null_gene_codes(data_merger):
    """Test handling of null values in Gene_Code column."""
    meth_df = pl.DataFrame({
        "Gene_Code": ["A", None, "C"],
        "Patient1": [0.1, 0.2, 0.3]
    })
    map_df = pl.DataFrame({
        "Gene_Code": ["A", "C"],
        "Actual_Gene_Name": ["Gene_A", "Gene_C"]
    })
    
    # Should handle nulls gracefully
    result = data_merger.merge(meth_df, map_df)
    assert result.shape[0] == 2  # Only non-null matches