import polars as pl
from polars.testing import assert_frame_equal
import pytest
from tcga.data.data_cleaner import DataCleaner

@pytest.fixture
def data_cleaner():
    """Provides a DataCleaner instance for testing."""
    return DataCleaner()

@pytest.fixture
def zero_filter_df():
    """Provides a sample DataFrame for testing the zero-filter."""
    return pl.DataFrame({
        "Gene_Name": ["GeneA_0_zeros", "GeneB_1_zero", "GeneC_2_zeros"],
        "Patient1": [1.0, 1.0, 0.0],
        "Patient2": [2.0, 0.0, 0.0],
    })

def test_clean_merged_df_removes_invalid_genes(data_cleaner):
    """
    Tests that rows with '.' in 'Actual_Gene_Name' are correctly removed.
    """
    input_df = pl.DataFrame({
        "Gene_Code": ["A", "B", "C"],
        "Actual_Gene_Name": ["GeneA", ".", "GeneC"],
        "Patient1": [1.0, 2.0, 3.0],
    })
    
    expected_df = pl.DataFrame({
        "Gene_Code": ["A", "C"],
        "Actual_Gene_Name": ["GeneA", "GeneC"],
        "Patient1": [1.0, 3.0],
    })

    cleaned_df = data_cleaner.clean_merged_df(input_df)
    assert_frame_equal(cleaned_df, expected_df)

def test_clean_merged_df_handles_na_and_dots(data_cleaner):
    """
    Tests that missing values (read as None) and '.' strings are converted to 0.0.
    """
    input_df = pl.DataFrame({
        "Gene_Code": ["A", "B", "C", "D"],
        "Actual_Gene_Name": ["GeneA", "GeneB", "GeneC", "GeneD"],
        "Patient1": ["1.5", None, None, "."],
    })
    
    expected_df = pl.DataFrame({
        "Gene_Code": ["A", "B", "C", "D"],
        "Actual_Gene_Name": ["GeneA", "GeneB", "GeneC", "GeneD"],
        "Patient1": [1.5, 0.0, 0.0, 0.0],
    })
    
    cleaned_df = data_cleaner.clean_merged_df(input_df)
    assert_frame_equal(cleaned_df, expected_df)

def test_filter_zero_percent_100(data_cleaner, zero_filter_df):
    """
    Tests that a 100% threshold removes nothing, as the condition is '< 100'.
    """
    retained_df = data_cleaner.filter_by_zero_percentage(
        zero_filter_df, zero_percent=100, id_cols=["Gene_Name"]
    )
    # The filter is strictly '<', so even a row with 100% zeros is not removed
    assert_frame_equal(retained_df, zero_filter_df)

def test_filter_zero_percent_50(data_cleaner, zero_filter_df):
    """
    Tests a 50% threshold, which should remove rows with 50% or more zeros.
    """
    retained_df = data_cleaner.filter_by_zero_percentage(
        zero_filter_df, zero_percent=50, id_cols=["Gene_Name"]
    )
    # GeneB (50%) and GeneC (100%) should be removed.
    assert retained_df.shape[0] == 1
    assert retained_df["Gene_Name"][0] == "GeneA_0_zeros"

def test_filter_zero_percent_0(data_cleaner, zero_filter_df):
    """
    Tests a 0% threshold, which should only keep rows with no zeros at all.
    """
    retained_df = data_cleaner.filter_by_zero_percentage(
        zero_filter_df, zero_percent=0, id_cols=["Gene_Name"]
    )
    # Only GeneA (which has 0% zeros) should remain.
    assert retained_df.shape[0] == 1
    assert retained_df["Gene_Name"][0] == "GeneA_0_zeros"