import pytest
from tcga.controller.controller import Controller
from pathlib import Path

def create_demo_files(tmp_path: Path, files_to_create: dict):
    """
    Creates the specified demo files in a temporary directory.
    """
    paths = {}
    
    if files_to_create.get('m'):
        content = "Gene_Code\tPatientA\tPatientB\ncg01\t0.1\t0.5\ncg02\t0.2\t0.6"
        p = tmp_path / "methylation.txt"; p.write_text(content); paths['m'] = str(p)
        
    if files_to_create.get('g'):
        content = "Gene_Code\tActual_Gene_Name\ncg01\tGENE_A\ncg02\tGENE_B,GENE_X"
        p = tmp_path / "gene_mapping.txt"; p.write_text(content); paths['g'] = str(p)

    if files_to_create.get('e'):
        content = "Gene_Name\tPatientA\tPatientB\nGENE_A\t100\t400\nGENE_B\t200\t500"
        p = tmp_path / "gene_expression.txt"; p.write_text(content); paths['e'] = str(p)

    if files_to_create.get('p'):
        content = "PatientID\tage\nPatientA\t55"
        p = tmp_path / "phenotype.txt"; p.write_text(content); paths['p'] = str(p)
        
    return paths

ALL_SCENARIOS = [
    ("row_1_meth_map",          {'m': True, 'g': True}, True, "meth_only"),
    ("row_2_meth_map_expr",     {'m': True, 'g': True, 'e': True}, True, "meth_and_expr"),
    ("row_3_all_files",         {'m': True, 'g': True, 'e': True, 'p': True}, True, "meth_and_expr_with_pheno"),
    ("row_4_meth_map_pheno",    {'m': True, 'g': True, 'p': True}, True, "meth_only_with_pheno"),
    ("row_5_expr_only",         {'e': True}, True, "expr_only"),
    ("row_6_expr_pheno",        {'e': True, 'p': True}, True, "expr_only_with_pheno"),
    ("row_7_meth_expr_pheno",   {'m': True, 'e': True, 'p': True}, False, "Methylation file was provided without a gene mapping file."),
    ("row_8_meth_expr",         {'m': True, 'e': True}, False, "Methylation file was provided without a gene mapping file."),
    ("row_9_meth_pheno",        {'m': True, 'p': True}, False, "Methylation file was provided without a gene mapping file."),
    ("row_10_meth_alone",       {'m': True}, False, "Methylation file was provided without a gene mapping file."),
    ("row_11_map_expr_pheno",   {'g': True, 'e': True, 'p': True}, False, "Gene mapping file was provided without a methylation file."),
    ("row_12_map_expr",         {'g': True, 'e': True}, False, "Gene mapping file was provided without a methylation file."),
    ("row_13_map_pheno",        {'g': True, 'p': True}, False, "Gene mapping file was provided without a methylation file."),
    ("row_14_map_alone",        {'g': True}, False, "Gene mapping file was provided without a methylation file."),
    ("row_15_pheno_alone",      {'p': True}, "no-op", None),
    ("row_16_no_files",         {}, "no-op", None),
]

@pytest.fixture
def controller():
    return Controller()

@pytest.mark.parametrize("test_id, files_dict, is_valid, outcome", ALL_SCENARIOS)
def test_all_16_e2e_scenarios(controller, tmp_path, test_id, files_dict, is_valid, outcome):
    paths = create_demo_files(tmp_path, files_dict)
    meth_p, map_p, expr_p, pheno_p = paths.get('m'), paths.get('g'), paths.get('e'), paths.get('p')

    if not is_valid:
        if is_valid == "no-op":
            final_meth, final_expr = controller.process_files(meth_p, map_p, expr_p, pheno_p)
            assert final_meth is None
            assert final_expr is None
        else:
            with pytest.raises(ValueError, match=outcome):
                controller.process_files(meth_p, map_p, expr_p, pheno_p)
        return

    final_meth, final_expr = controller.process_files(
        meth_p, map_p, expr_p, pheno_p, selected_phenotypes=["age"], zero_percent=100
    )

    if outcome == "meth_and_expr_with_pheno":
        assert final_meth.shape[0] == 3
        assert final_expr.shape[0] == 3
        assert "GENE_B,GENE_X" in final_meth["Actual_Gene_Name"].to_list()