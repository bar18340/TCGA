import polars as pl
from polars.testing import assert_frame_equal
import pytest
from tcga.data.file_handler import FileHandler

@pytest.fixture
def file_handler():
    """Provides a FileHandler instance for testing."""
    return FileHandler()

def test_load_dataframe_success_methylation(file_handler, tmp_path):
    """
    Tests successful loading of a valid methylation file.
    """
    file_content = "Composite Element REF\tPatient1\tPatient2\n" \
                   "cg00000029\t0.2\t0.8\n" \
                   "cg00000108\t0.5\t0.5"
    p = tmp_path / "methylation.txt"
    p.write_text(file_content)
    
    expected_df = pl.DataFrame({
        "Gene_Code": ["cg00000029", "cg00000108"],
        "Patient1": [0.2, 0.5],
        "Patient2": [0.8, 0.5]
    })

    df = file_handler.load_dataframe(str(p), 'methylation')

    assert_frame_equal(df, expected_df)

def test_load_dataframe_success_gene_expression(file_handler, tmp_path):
    """
    Tests successful loading of a valid gene expression file.
    It should rename the first column to 'Gene_Name'.
    """
    file_content = "Hugo_Symbol\tPatientA\tPatientB\n" \
                   "GNAI1\t100\t200\n" \
                   "GNAS\t300\t400"
    p = tmp_path / "expression.txt"
    p.write_text(file_content)

    expected_df = pl.DataFrame({
        "Gene_Name": ["GNAI1", "GNAS"],
        "PatientA": [100, 300],
        "PatientB": [200, 400]
    })

    df = file_handler.load_dataframe(str(p), 'gene_expression')
    
    assert_frame_equal(df, expected_df)


def test_load_dataframe_success_gene_mapping(file_handler, tmp_path):
    """
    Tests successful loading of a valid gene mapping file.
    It should correctly select and rename the first two columns.
    """
    file_content = "Gene_Code\tActual_Gene_Name\tOther_Info\n" \
                   "cg01\tGENE1\tinfo1\n" \
                   "cg02\tGENE2\tinfo2"
    p = tmp_path / "mapping.txt"
    p.write_text(file_content)

    expected_df = pl.DataFrame({
        "Gene_Code": ["cg01", "cg02"],
        "Actual_Gene_Name": ["GENE1", "GENE2"]
    })

    df = file_handler.load_dataframe(str(p), 'gene_mapping')

    assert_frame_equal(df, expected_df)

def test_load_dataframe_file_not_found(file_handler):
    """
    Tests that a warning is logged and None is returned if the file path is invalid.
    """
    result = file_handler.load_dataframe("non_existent_file.txt", 'methylation')

    assert result is None

def test_load_dataframe_invalid_mapping_file_raises_error(file_handler, tmp_path):
    """
    Tests that a ValueError is raised if the gene mapping file has fewer than two columns.
    """
    file_content = "OnlyOneColumn\nGene1\nGene2"
    p = tmp_path / "invalid_mapping.txt"
    p.write_text(file_content)

    with pytest.raises(ValueError, match="Gene mapping file must have at least two columns."):
        file_handler.load_dataframe(str(p), 'gene_mapping')

def test_logs_warning_on_duplicate_gene_names(file_handler, tmp_path, caplog):
    """
    Tests that a warning is logged if the gene expression file contains duplicate gene names.
    """
    file_content = "Gene_Name\tPatient1\n" \
                   "GENE_A\t10\n" \
                   "GENE_A\t20"
    p = tmp_path / "duplicate_expr.txt"
    p.write_text(file_content)

    with caplog.at_level("WARNING"):
        file_handler.load_dataframe(str(p), 'gene_expression')

    assert "Duplicate Gene_Name entries found" in caplog.text