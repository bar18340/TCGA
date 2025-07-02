"""
TCGA Web Application (Flask)

This Flask app provides a web interface for uploading, validating, processing, and saving TCGA data files.
It supports methylation, gene mapping, gene expression, and phenotype files, and uses the TCGA Controller
to orchestrate all data processing logic.

Key Features:
- Handles file uploads and validation for all supported TCGA data types.
- Validates required file combinations (e.g., methylation requires mapping).
- Uses temporary files for uploaded data to avoid memory issues.
- Delegates all processing to the Controller, which manages cleaning, merging, and alignment.
- Saves processed outputs to user-specified folders with unique filenames.
- Provides user feedback via Flask flash messages.
- Supports previewing phenotype file columns via AJAX.

Usage:
- Start the Flask app and navigate to the root URL.
- Upload the required files and specify output options.
- Download processed files from the output location.
"""

import os, sys
import polars as pl
from flask import Flask, render_template, request, redirect, flash
from tcga.controller.controller import Controller
from tcga.utils.logger import setup_logger
import tempfile

# --- Flask App Config ---
# If we're running as a PyInstaller bundle, sys.frozen is True
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(os.path.dirname(__file__))

# Point Flask at the temp‐extracted templates and static folders
template_folder = os.path.join(base_path, 'templates')
static_folder   = os.path.join(base_path, 'static')

app = Flask(
    __name__,
    template_folder=template_folder,
    static_folder=static_folder
)
# print("✅ Flask app initialized")
app.secret_key = 'tcga_secret_key'

# --- Use existing TCGA controller logic ---
logger = setup_logger()
controller = Controller(logger=logger)

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main route for file upload and processing.

    - Handles both GET (form display) and POST (file upload/processing) requests.
    - Validates file combinations and user input.
    - Saves uploaded files to temporary disk locations.
    - Calls the TCGA Controller to process files.
    - Saves processed outputs to the user-specified folder.
    - Cleans up all temporary files.
    - Renders the main template with results or error messages.
    """
    if request.method == 'POST':
        try:
            # --- Handle uploaded files ---
            methylation_file = request.files.get('methylation_file')
            mapping_file = request.files.get('mapping_file')
            expression_file = request.files.get('expression_file')
            phenotype_file = request.files.get('phenotype_file')
            # --- Validate presence of at least one file ---
            if not any([methylation_file, mapping_file, expression_file, phenotype_file]):
                flash("❌ Please upload at least one input file.", "error")
                return redirect('/')
            # Validate minimum input file requirements
            if phenotype_file and not any([methylation_file, mapping_file, expression_file]):
                flash("❌ A phenotype file must be uploaded together with a gene expression file or methylation + mapping files.", "error")
                return redirect('/')
            if methylation_file and not mapping_file:
                flash("❌ A methylation file must be uploaded together with a mapping file.", "error")
                return redirect('/')
            if mapping_file and not methylation_file:
                flash("❌ A mapping file must be uploaded together with a methylation file.", "error")
                return redirect('/')
            save_path = request.form.get('save_folder')
            if not save_path:
                flash("❌ Please choose a destination folder to save output files.", "error")
                return redirect('/')
            zero_threshold = float(request.form.get('zero_threshold', 100))
            selected_phenos = request.form.getlist('phenos')
            
            base_filename = request.form.get('output_filename', '').strip() or 'merged_output'

            # --- Save uploaded files ---
            file_paths = {}
            for label, file in {
                'methylation': methylation_file,
                'gene_mapping': mapping_file,
                'gene_expression': expression_file,
                'phenotype': phenotype_file
            }.items():
                if file and file.filename:
                    # Save file to a temporary file on disk
                    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='wb')
                    temp.write(file.read())
                    temp.flush()
                    temp.close()
                    file_paths[label] = temp.name

            # --- Run TCGA controller logic ---
            result = controller.process_files(
                methylation_path=file_paths.get('methylation'),
                gene_mapping_path=file_paths.get('gene_mapping'),
                gene_expression_path=file_paths.get('gene_expression'),
                phenotype_path=file_paths.get('phenotype'),
                selected_phenotypes=selected_phenos,
                zero_percent=zero_threshold
            )

            # --- Save final outputs to .csv ---
            if not result or not isinstance(result, tuple):
                flash("❌ Internal error: Unexpected result structure from processing.", "error")
                return redirect('/')
            df1, _, df2, _ = result if len(result) == 4 else (*result, None, None)

            output_paths = []

            def get_unique_filename(folder, base, suffix):
                counter = 1
                filename = f"{base}_{suffix}.csv"
                path = os.path.join(folder, filename)
                while os.path.exists(path):
                    filename = f"{base}_{suffix}_{counter}.csv"
                    path = os.path.join(folder, filename)
                    counter += 1
                return path
            
            if df1 is not None and df2 is None:
                if 'gene_expression' in file_paths:
                    # Single expression file cleaned
                    out_expr_path = get_unique_filename(save_path, base_filename, 'expression')
                    df1.write_csv(out_expr_path)
                    output_paths.append({"label": os.path.basename(out_expr_path)})
                else:
                    # Methylation + mapping cleaned
                    out_meth_path = get_unique_filename(save_path, base_filename, 'methylation')
                    df1.write_csv(out_meth_path)
                    output_paths.append({"label": os.path.basename(out_meth_path)})

            elif df1 is not None and df2 is not None:
                # Both methylation and expression processed
                out_meth_path = get_unique_filename(save_path, base_filename, 'methylation')
                out_expr_path = get_unique_filename(save_path, base_filename, 'expression')
                df1.write_csv(out_meth_path)
                df2.write_csv(out_expr_path)
                output_paths.extend([
                    {"label": os.path.basename(out_meth_path)},
                    {"label": os.path.basename(out_expr_path)}
                ])

            # --- Clean up temp files ---
            for path in file_paths.values():
                try:
                    os.remove(path)
                except Exception:
                    pass

            return render_template('index.html', success=True, outputs=output_paths)

        except Exception as e:
            flash(f"❌ Error: {e}", 'error')
            return redirect('/')

    return render_template('index.html')


@app.route('/reset')
def reset():
    """
    Route to reset the application state (simply redirects to main page).
    """
    # flash("App has been reset.", 'info')
    return redirect('/')

@app.route('/preview_phenotype', methods=['POST'])
def preview_phenotype():
    """
    Route to preview phenotype file columns before processing.

    - Accepts a phenotype file upload via POST.
    - Returns a JSON response with the column headers (excluding patient ID).
    - Used for dynamic UI updates (AJAX).
    """
    file = request.files.get('phenotype_file')
    if not file:
        return {"error": "No file uploaded"}, 400

    try:
        df = pl.read_csv(file, separator='\t', infer_schema_length=10000)
        headers = df.columns[1:]  # Skip patient ID column
        return {"columns": headers}
    except Exception as e:
        return {"error": str(e)}, 500
