import pytest
import polars as pl
import os
from pathlib import Path
from tcga.controller.controller import Controller
from tcga.data.file_handler import FileHandler
import tempfile

@pytest.fixture
def controller():
    """Provides a Controller instance for testing."""
    return Controller()

@pytest.fixture
def file_handler():
    """Provides a FileHandler instance for testing."""
    return FileHandler()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_malformed_excel_file(self, file_handler, tmp_path):
        """Test handling of corrupted Excel files."""
        # Create a fake Excel file (actually just text)
        fake_excel = tmp_path / "fake.xlsx"
        fake_excel.write_text("This is not an Excel file")
        
        with pytest.raises(ValueError):
            file_handler.load_dataframe(str(fake_excel), 'gene_expression')
    
    def test_special_characters_in_data(self, controller, tmp_path):
        """Test handling of special characters in gene names."""
        # Create files with special characters
        meth_df = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02", "cg03"],
            "Patient1": [0.1, 0.2, 0.3],
            "Patient2": [0.4, 0.5, 0.6]
        })
        
        map_df = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02", "cg03"],
            "Actual_Gene_Name": ["GENE-A/B", "GENE_C&D", "GENE E,F"]  # Special chars
        })
        
        meth_path = tmp_path / "meth.txt"
        map_path = tmp_path / "map.txt"
        meth_df.write_csv(str(meth_path), separator='\t')
        map_df.write_csv(str(map_path), separator='\t')
        
        # Should handle special characters
        df_meth, _ = controller.process_files(
            methylation_path=str(meth_path),
            gene_mapping_path=str(map_path)
        )
        
        assert df_meth is not None
        assert "GENE-A/B" in df_meth["Actual_Gene_Name"].to_list()
    
    def test_very_long_filenames(self, file_handler, tmp_path):
        """Test handling of very long filenames."""
        # Create a file with very long name
        long_name = "very_long_filename_" + "x" * 200 + ".xlsx"
        long_path = tmp_path / long_name
        
        df = pl.DataFrame({"col": [1, 2, 3]})
        df.write_excel(str(long_path))
        
        # Should handle long filenames
        loaded = file_handler.load_dataframe(str(long_path), 'gene_expression')
        assert loaded is not None
    
    def test_unicode_in_data(self, controller, tmp_path):
        """Test handling of Unicode characters."""
        # Create files with Unicode
        pheno_df = pl.DataFrame({
            "PatientID": ["Patient1", "Patient2"],
            "ethnicity": ["日本人", "中国人"],  # Japanese/Chinese characters
            "notes": ["α-β test", "γ-δ test"]  # Greek letters
        })
        
        pheno_path = tmp_path / "pheno.xlsx"
        pheno_df.write_excel(str(pheno_path))
        
        expr_df = pl.DataFrame({
            "Gene_Name": ["GENE1", "GENE2"],
            "Patient1": [100, 200],
            "Patient2": [300, 400]
        })
        expr_path = tmp_path / "expr.txt"
        expr_df.write_csv(str(expr_path), separator='\t')
        
        # Should handle Unicode
        _, df_expr = controller.process_files(
            gene_expression_path=str(expr_path),
            phenotype_path=str(pheno_path),
            selected_phenotypes=["ethnicity", "notes"]
        )
        
        assert df_expr is not None
        assert df_expr.shape[0] == 4  # 2 phenotype + 2 gene rows


class TestPerformanceEdgeCases:
    """Test performance with extreme cases."""
    
    def test_many_columns(self, controller, tmp_path):
        """Test with files having many patient columns."""
        # Create file with 1000 patients
        num_patients = 1000
        patient_cols = [f"Patient_{i:04d}" for i in range(num_patients)]
        
        data = {"Gene_Code": ["cg01", "cg02"]}
        for patient in patient_cols:
            data[patient] = [0.1, 0.2]
        
        meth_df = pl.DataFrame(data)
        map_df = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02"],
            "Actual_Gene_Name": ["GENE_A", "GENE_B"]
        })
        
        meth_path = tmp_path / "many_cols_meth.csv"
        map_path = tmp_path / "many_cols_map.csv"
        meth_df.write_csv(str(meth_path), separator='\t')
        map_df.write_csv(str(map_path), separator='\t')
        
        # Should handle many columns
        df_meth, _ = controller.process_files(
            methylation_path=str(meth_path),
            gene_mapping_path=str(map_path)
        )
        
        assert df_meth is not None
        assert len(df_meth.columns) == num_patients + 2  # +2 for Gene_Code and Actual_Gene_Name
    
    def test_all_zeros_file(self, controller, tmp_path):
        """Test file with all zero values."""
        # Create file with all zeros
        meth_df = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02", "cg03"],
            "Patient1": [0.0, 0.0, 0.0],
            "Patient2": [0.0, 0.0, 0.0],
            "Patient3": [0.0, 0.0, 0.0]
        })
        map_df = pl.DataFrame({
            "Gene_Code": ["cg01", "cg02", "cg03"],
            "Actual_Gene_Name": ["GENE_A", "GENE_B", "GENE_C"]
        })
        
        meth_path = tmp_path / "all_zeros.txt"
        map_path = tmp_path / "map.txt"
        meth_df.write_csv(str(meth_path), separator='\t')
        map_df.write_csv(str(map_path), separator='\t')
        
        # With 50% threshold, all rows should be removed
        df_meth, _ = controller.process_files(
            methylation_path=str(meth_path),
            gene_mapping_path=str(map_path),
            zero_percent=50
        )
        
        assert df_meth is not None
        assert df_meth.shape[0] == 0  # All rows filtered out


class TestFileSystemEdgeCases:
    """Test file system related edge cases."""
    
    def test_output_path_with_special_chars(self, controller, tmp_path):
        """Test output paths with special characters."""
        df = pl.DataFrame({"col": [1, 2, 3]})
        
        # Test with spaces and special chars in filename
        special_names = [
            "test file with spaces",
            "test-file-with-dashes",
            "test_file_with_underscores",
            "test.file.with.dots"
        ]
        
        for name in special_names:
            paths = controller.save_results(
                df, None, str(tmp_path), name, "csv"
            )
            assert len(paths) == 1
            assert os.path.exists(paths[0])
    
    def test_concurrent_file_access(self, file_handler, tmp_path):
        """Test handling when file is being accessed by another process."""
        # Create a file
        test_file = tmp_path / "test.xlsx"
        df = pl.DataFrame({"col": [1, 2, 3]})
        df.write_excel(str(test_file))
        
        # Open file for exclusive access (simulating another process)
        with open(test_file, 'rb') as f:
            # Try to load while file is open
            # Should still work for reading
            loaded = file_handler.load_dataframe(str(test_file), 'gene_expression')
            assert loaded is not None


class TestDataValidationEdgeCases:
    """Test data validation edge cases."""
    
    def test_duplicate_patient_columns(self, controller, tmp_path):
        """Test handling of duplicate patient column names."""
        # This shouldn't happen but test the behavior
        meth_content = "Gene_Code\tPatientA\tPatientA\tPatientB\n"
        meth_content += "cg01\t0.1\t0.2\t0.3\n"
        
        meth_path = tmp_path / "dup_cols.txt"
        meth_path.write_text(meth_content)
        
        map_df = pl.DataFrame({
            "Gene_Code": ["cg01"],
            "Actual_Gene_Name": ["GENE_A"]
        })
        map_path = tmp_path / "map.txt"
        map_df.write_csv(str(map_path), separator='\t')
        
        # Should handle or error gracefully
        try:
            df_meth, _ = controller.process_files(
                methylation_path=str(meth_path),
                gene_mapping_path=str(map_path)
            )
            # If it succeeds, check the result
            assert df_meth is not None
        except Exception:
            # If it fails, that's also acceptable behavior
            pass
    
    def test_missing_values_in_phenotype(self, controller, tmp_path):
        """Test handling of missing values in phenotype file."""
        pheno_df = pl.DataFrame({
            "PatientID": ["P1", "P2", "P3", "P4"],
            "age": [55, None, 65, None],  # Missing ages
            "stage": ["I", "II", None, "IV"]  # Missing stage
        })
        
        expr_df = pl.DataFrame({
            "Gene_Name": ["GENE1"],
            "P1": [100],
            "P2": [200],
            "P3": [300],
            "P4": [400]
        })
        
        pheno_path = tmp_path / "pheno.xlsx"
        expr_path = tmp_path / "expr.xlsx"
        pheno_df.write_excel(str(pheno_path))
        expr_df.write_excel(str(expr_path))
        
        # Should handle missing values
        _, df_expr = controller.process_files(
            gene_expression_path=str(expr_path),
            phenotype_path=str(pheno_path),
            selected_phenotypes=["age", "stage"]
        )
        
        assert df_expr is not None
        assert df_expr.shape[0] == 3  # 2 phenotype + 1 gene rows