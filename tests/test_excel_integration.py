import pytest
import polars as pl
from pathlib import Path
import os
import tempfile
from tcga.data.file_handler import FileHandler
from tcga.controller.controller import Controller

@pytest.fixture
def file_handler():
    """Provides a FileHandler instance for testing."""
    return FileHandler()

@pytest.fixture
def controller():
    """Provides a Controller instance for testing."""
    return Controller()

class TestExcelFileHandling:
    """Test Excel file reading and writing functionality."""
    
    def test_detect_file_format(self, file_handler):
        """Test file format detection."""
        assert file_handler._detect_file_format("test.xlsx") == "excel"
        assert file_handler._detect_file_format("test.xls") == "excel"
        assert file_handler._detect_file_format("test.xlsm") == "excel"
        assert file_handler._detect_file_format("test.xlsb") == "excel"
        assert file_handler._detect_file_format("test.csv") == "csv"
        assert file_handler._detect_file_format("test.txt") == "csv"
        assert file_handler._detect_file_format("test.tsv") == "csv"
        assert file_handler._detect_file_format("test") == "csv"  # No extension defaults to csv

    def test_read_excel_file(self, file_handler, tmp_path):
        """Test reading Excel files."""
        # Create test Excel file
        test_df = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02", "cg03"],
            "Patient1": [0.1, 0.2, 0.3],
            "Patient2": [0.4, 0.5, 0.6]
        })
        excel_path = tmp_path / "test.xlsx"
        test_df.write_excel(str(excel_path))
        
        # Test reading
        loaded_df = file_handler._read_file(str(excel_path))
        assert loaded_df is not None
        assert loaded_df.shape == test_df.shape
        assert loaded_df.columns == test_df.columns

    def test_save_excel_file(self, file_handler, tmp_path):
        """Test saving DataFrames as Excel files."""
        test_df = pl.DataFrame({
            "Gene_Name": ["GENE1", "GENE2", "GENE3"],
            "Sample1": [1.0, 2.0, 3.0],
            "Sample2": [4.0, 5.0, 6.0]
        })
        
        # Test saving as Excel
        output_path = str(tmp_path / "output_test")
        file_handler.save_dataframe(test_df, output_path, 'excel')
        
        # Check file was created with correct extension
        expected_path = output_path + ".xlsx"
        assert os.path.exists(expected_path)
        
        # Read back and verify
        loaded_df = pl.read_excel(expected_path)
        assert loaded_df.shape == test_df.shape

    def test_save_csv_file(self, file_handler, tmp_path):
        """Test saving DataFrames as CSV files."""
        test_df = pl.DataFrame({
            "Gene_Name": ["GENE1", "GENE2", "GENE3"],
            "Sample1": [1.0, 2.0, 3.0],
            "Sample2": [4.0, 5.0, 6.0]
        })
        
        # Test saving as CSV
        output_path = str(tmp_path / "output_test")
        file_handler.save_dataframe(test_df, output_path, 'csv')
        
        # Check file was created with correct extension
        expected_path = output_path + ".csv"
        assert os.path.exists(expected_path)
        
        # Read back and verify
        loaded_df = pl.read_csv(expected_path)
        assert loaded_df.shape == test_df.shape


class TestMixedFormatProcessing:
    """Test processing with mixed CSV and Excel input files."""
    
    def test_csv_methylation_excel_expression(self, controller, tmp_path):
        """Test CSV methylation/mapping with Excel expression file."""
        # Create CSV files
        meth_csv = tmp_path / "methylation.txt"
        meth_csv.write_text("Gene_Code\tPatientA\tPatientB\ncg01\t0.1\t0.5\ncg02\t0.2\t0.6")
        
        map_csv = tmp_path / "mapping.txt"
        map_csv.write_text("Gene_Code\tActual_Gene_Name\ncg01\tGENE_A\ncg02\tGENE_B")
        
        # Create Excel expression file
        expr_df = pl.DataFrame({
            "Gene_Name": ["GENE_A", "GENE_B"],
            "PatientA": [100, 200],
            "PatientB": [300, 400]
        })
        expr_xlsx = tmp_path / "expression.xlsx"
        expr_df.write_excel(str(expr_xlsx))
        
        # Process mixed format files
        df_meth, df_expr = controller.process_files(
            methylation_path=str(meth_csv),
            gene_mapping_path=str(map_csv),
            gene_expression_path=str(expr_xlsx)
        )
        
        assert df_meth is not None
        assert df_expr is not None
        assert df_meth.shape[0] == 2
        assert df_expr.shape[0] == 2

    def test_excel_methylation_csv_expression(self, controller, tmp_path):
        """Test Excel methylation/mapping with CSV expression file."""
        # Create Excel files
        meth_df = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02"],
            "PatientA": [0.1, 0.2],
            "PatientB": [0.5, 0.6]
        })
        meth_xlsx = tmp_path / "methylation.xlsx"
        meth_df.write_excel(str(meth_xlsx))
        
        map_df = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02"],
            "Actual_Gene_Name": ["GENE_A", "GENE_B"]
        })
        map_xlsx = tmp_path / "mapping.xlsx"
        map_df.write_excel(str(map_xlsx))
        
        # Create CSV expression file
        expr_csv = tmp_path / "expression.txt"
        expr_csv.write_text("Gene_Name\tPatientA\tPatientB\nGENE_A\t100\t300\nGENE_B\t200\t400")
        
        # Process mixed format files
        df_meth, df_expr = controller.process_files(
            methylation_path=str(meth_xlsx),
            gene_mapping_path=str(map_xlsx),
            gene_expression_path=str(expr_csv)
        )
        
        assert df_meth is not None
        assert df_expr is not None


class TestControllerSaveResults:
    """Test the new save_results method in Controller."""
    
    def test_save_results_csv(self, controller, tmp_path):
        """Test saving results in CSV format."""
        # Create test DataFrames
        df_meth = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02"],
            "Actual_Gene_Name": ["GENE_A", "GENE_B"],
            "Patient1": ["0.1", "0.2"],
            "Patient2": ["0.3", "0.4"]
        })
        
        df_expr = pl.DataFrame({
            "Gene_Name": ["GENE_A", "GENE_B"],
            "Patient1": ["100", "200"],
            "Patient2": ["300", "400"]
        })
        
        # Save as CSV
        output_paths = controller.save_results(
            df_meth, df_expr, str(tmp_path), "test_output", "csv"
        )
        
        assert len(output_paths) == 2
        assert all(path.endswith('.csv') for path in output_paths)
        assert all(os.path.exists(path) for path in output_paths)

    def test_save_results_excel(self, controller, tmp_path):
        """Test saving results in Excel format."""
        # Create test DataFrames
        df_meth = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02"],
            "Actual_Gene_Name": ["GENE_A", "GENE_B"],
            "Patient1": ["0.1", "0.2"],
            "Patient2": ["0.3", "0.4"]
        })
        
        df_expr = pl.DataFrame({
            "Gene_Name": ["GENE_A", "GENE_B"],
            "Patient1": ["100", "200"],
            "Patient2": ["300", "400"]
        })
        
        # Save as Excel
        output_paths = controller.save_results(
            df_meth, df_expr, str(tmp_path), "test_output", "excel"
        )
        
        assert len(output_paths) == 2
        assert all(path.endswith('.xlsx') for path in output_paths)
        assert all(os.path.exists(path) for path in output_paths)

    def test_save_results_unique_filenames(self, controller, tmp_path):
        """Test that save_results generates unique filenames."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        
        # First save
        paths1 = controller.save_results(df, None, str(tmp_path), "test", "csv")
        assert len(paths1) == 1
        
        # Second save with same name should create unique filename
        paths2 = controller.save_results(df, None, str(tmp_path), "test", "csv")
        assert len(paths2) == 1
        assert paths1[0] != paths2[0]
        assert "test_methylation_1.csv" in paths2[0]


class TestExcelWithPhenotype:
    """Test Excel files with phenotype data."""
    
    def test_excel_files_with_phenotype(self, controller, tmp_path):
        """Test processing Excel files with phenotype selection."""
        # Create all Excel files
        meth_df = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02"],
            "PatientA": [0.1, 0.2],
            "PatientB": [0.5, 0.6]
        })
        meth_xlsx = tmp_path / "methylation.xlsx"
        meth_df.write_excel(str(meth_xlsx))
        
        map_df = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02"],
            "Actual_Gene_Name": ["GENE_A", "GENE_B"]
        })
        map_xlsx = tmp_path / "mapping.xlsx"
        map_df.write_excel(str(map_xlsx))
        
        expr_df = pl.DataFrame({
            "Gene_Name": ["GENE_A", "GENE_B"],
            "PatientA": [100, 200],
            "PatientB": [300, 400]
        })
        expr_xlsx = tmp_path / "expression.xlsx"
        expr_df.write_excel(str(expr_xlsx))
        
        pheno_df = pl.DataFrame({
            "PatientID": ["PatientA", "PatientB"],
            "age": [55, 60],
            "stage": ["I", "II"]
        })
        pheno_xlsx = tmp_path / "phenotype.xlsx"
        pheno_df.write_excel(str(pheno_xlsx))
        
        # Process with phenotype
        df_meth, df_expr = controller.process_files(
            methylation_path=str(meth_xlsx),
            gene_mapping_path=str(map_xlsx),
            gene_expression_path=str(expr_xlsx),
            phenotype_path=str(pheno_xlsx),
            selected_phenotypes=["age", "stage"]
        )
        
        assert df_meth is not None
        assert df_expr is not None
        # Should have 2 phenotype rows + 2 gene rows
        assert df_meth.shape[0] == 4
        assert df_expr.shape[0] == 4
        # Check phenotype rows are at the top
        assert df_meth["Actual_Gene_Name"][0] == "age"
        assert df_meth["Actual_Gene_Name"][1] == "stage"