"""
TCGA Web Application (Flask)

This Flask app provides a web interface for uploading, validating, processing, and saving TCGA data files.
It supports methylation, gene mapping, gene expression, and phenotype files in both CSV and Excel formats,
and uses the TCGA Controller to orchestrate all data processing logic.

Key Features:
- Handles file uploads and validation for all supported TCGA data types in CSV and Excel formats.
- Validates required file combinations (e.g., methylation requires mapping).
- Uses temporary files for uploaded data to avoid memory issues.
- Delegates all processing to the Controller, which manages cleaning, merging, and alignment.
- Saves processed outputs to user-specified folders with unique filenames in CSV or Excel format.
- Provides user feedback via Flask flash messages.
- Supports previewing phenotype file columns via AJAX.

Usage:
- Start the Flask app and navigate to the root URL.
- Upload the required files and specify output options.
- Download processed files from the output location.
"""

import os, sys
import polars as pl
from flask import Flask, render_template, request, redirect, flash, session
from tcga.controller.controller import Controller
from tcga.utils.logger import setup_logger
import tempfile
import configparser

# --- Flask App Config ---
# If we're running as a PyInstaller bundle, sys.frozen is True
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    config_file_path = os.path.join(os.path.dirname(sys.executable), 'config.ini')
else:
    base_path = os.path.abspath(os.path.dirname(__file__))
    config_file_path = os.path.join(os.path.dirname(base_path), 'config.ini')

# Point Flask at the temp‐extracted templates and static folders
template_folder = os.path.join(base_path, 'templates')
static_folder   = os.path.join(base_path, 'static')

app = Flask(
    __name__,
    template_folder=template_folder,
    static_folder=static_folder
)

# Automatic secret key logic
config = configparser.ConfigParser()
# Check if the config file exists and has a valid key.
try:
    config.read(config_file_path)
    secret_key = config.get('Flask', 'SECRET_KEY')
    if not secret_key:
        raise ValueError("SECRET_KEY is empty.")
except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
    # If the file or key doesn't exist, create it.
    print("No valid secret key found. Generating a new one.")
    secret_key = os.urandom(24).hex()
    config['Flask'] = {'SECRET_KEY': secret_key}
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)

app.secret_key = secret_key

# Use existing TCGA controller logic
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
    # Clear any previous success data from session when loading the page fresh
    if request.method == 'GET':
        session.pop('success_data', None)
        
    if request.method == 'POST':
        try:
            # --- Handle uploaded files ---
            methylation_file = request.files.get('methylation_file')
            mapping_file = request.files.get('mapping_file')
            expression_file = request.files.get('expression_file')
            phenotype_file = request.files.get('phenotype_file')
            
            # --- Validate file combinations FIRST ---
            has_methylation = methylation_file and methylation_file.filename
            has_mapping = mapping_file and mapping_file.filename
            has_expression = expression_file and expression_file.filename
            has_phenotype = phenotype_file and phenotype_file.filename
            
            # Check if at least one file is provided
            if not any([has_methylation, has_mapping, has_expression, has_phenotype]):
                flash("Please upload at least one input file.", "error")
                return render_template('index.html')
            
            # Define valid combinations
            valid_combo = False
            if (has_methylation and has_mapping and not has_expression and not has_phenotype) or \
               (has_methylation and has_mapping and has_expression and not has_phenotype) or \
               (has_methylation and has_mapping and has_expression and has_phenotype) or \
               (has_methylation and has_mapping and not has_expression and has_phenotype) or \
               (not has_methylation and not has_mapping and has_expression and not has_phenotype) or \
               (not has_methylation and not has_mapping and has_expression and has_phenotype):
                valid_combo = True
            
            if not valid_combo:
                # Provide specific error messages
                if has_methylation and not has_mapping:
                    flash("A methylation file must be uploaded together with a gene mapping file.", "error")
                elif has_mapping and not has_methylation:
                    flash("A gene mapping file must be uploaded together with a methylation file.", "error")
                elif has_phenotype and not has_methylation and not has_expression:
                    flash("A phenotype file must be uploaded together with a gene expression file or methylation + mapping files.", "error")
                else:
                    flash("Invalid file combination. Please check the required file combinations.", "error")
                return render_template('index.html')
            
            # --- Get other form data ---
            save_path = request.form.get('save_folder')
            if not save_path:
                flash("Please choose a destination folder to save output files.", "error")
                return render_template('index.html')
            
            zero_threshold = float(request.form.get('zero_threshold', 100))
            selected_phenos = request.form.getlist('phenos')
            output_format = request.form.get('output_format', 'csv')
            base_filename = request.form.get('output_filename', '').strip() or 'merged_output'

            # --- Save uploaded files and check sizes ---
            file_paths = {}
            temp_files = []
            total_size = 0
            SIZE_LIMIT_MB = 50  # 50 MB limit for Excel output
            
            # First, check file sizes before processing
            file_sizes = {}
            for file_name, file in [
                ('methylation', methylation_file),
                ('mapping', mapping_file),
                ('expression', expression_file),
                ('phenotype', phenotype_file)
            ]:
                if file and file.filename:
                    # Reset file pointer to beginning
                    file.seek(0, 2)  # Seek to end
                    file_size = file.tell()  # Get file size
                    total_size += file_size
                    file_sizes[file_name] = file_size
                    file.seek(0)  # Reset to beginning for reading
                    logger.info(f"{file_name} file size: {file_size / 1024 / 1024:.2f} MB")
            
            logger.info(f"Total file size: {total_size / 1024 / 1024:.2f} MB")
            
            # Check if we should force CSV output based on file size
            force_csv = False
            if output_format == 'excel' and total_size > SIZE_LIMIT_MB * 1024 * 1024:
                output_format = 'csv'
                force_csv = True
                logger.info(f"Large files detected. Forcing CSV output.")
            
            # Now save the files
            for label, file in {
                'methylation': methylation_file,
                'gene_mapping': mapping_file,
                'gene_expression': expression_file,
                'phenotype': phenotype_file
            }.items():
                if file and file.filename:
                    # Get the file extension to preserve it
                    ext = os.path.splitext(file.filename)[1]
                    # Save file to a temporary file on disk with proper extension
                    temp = tempfile.NamedTemporaryFile(delete=False, suffix=ext, mode='wb')
                    file.seek(0)  # Reset file pointer
                    temp.write(file.read())
                    temp.close()
                    file_paths[label] = temp.name
                    temp_files.append(temp.name)
            
            # --- Run TCGA controller logic ---
            df_meth, df_expr = controller.process_files(
                methylation_path=file_paths.get('methylation'),
                gene_mapping_path=file_paths.get('gene_mapping'),
                gene_expression_path=file_paths.get('gene_expression'),
                phenotype_path=file_paths.get('phenotype'),
                selected_phenotypes=selected_phenos,
                zero_percent=zero_threshold
            )

            # --- Save output files using the controller's save method ---
            output_paths = controller.save_results(
                df_meth, df_expr, save_path, base_filename, output_format
            )
            
            # Clean up temp files
            for path in temp_files:
                try:
                    os.remove(path)
                except Exception:
                    pass

            if not output_paths:
                flash("✅ Process completed, but no output files were generated based on the inputs.", "info")
                return render_template('index.html')
            
            # Show message if format was forced to CSV
            if force_csv:
                flash(f"ℹ️ Large files detected ({total_size / 1024 / 1024:.1f} MB total). CSV format was used for optimal performance and to prevent system freezing.", "info")

            # Format output paths for display
            output_info = [{"label": os.path.basename(path)} for path in output_paths]
            
            # Store success data in session to persist it
            session['success_data'] = {
                'success': True,
                'outputs': output_info
            }
            
            # Use render_template instead of redirect to show success immediately
            return render_template('index.html', success=True, outputs=output_info)

        except Exception as e:
            flash(f"❌ Error: {e}", 'error')
            return render_template('index.html')

    # GET request - check if we have success data in session
    success_data = session.get('success_data', {})
    if success_data:
        # Clear it from session after retrieving
        session.pop('success_data', None)
        return render_template('index.html', **success_data)
    
    return render_template('index.html')

@app.route('/reset')
def reset():
    """
    Route to reset the application state and clear session data.
    """
    session.pop('success_data', None)
    # Don't use flash message for reset to keep it clean
    return redirect('/')

@app.route('/preview_phenotype', methods=['POST'])
def preview_phenotype():
    """
    Route to preview phenotype file columns before processing.

    - Accepts a phenotype file upload via POST.
    - Returns a JSON response with the column headers (excluding patient ID).
    - Used for dynamic UI updates (AJAX).
    - Supports both CSV and Excel files.
    """
    file = request.files.get('phenotype_file')
    if not file:
        return {"error": "No file uploaded"}, 400

    try:
        # Save to temporary file to read it
        ext = os.path.splitext(file.filename)[1] if file.filename else '.txt'
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        # Detect file format and read accordingly
        ext_lower = ext.lower()
        if ext_lower in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            # Read Excel file with multiple attempts
            try:
                df = pl.read_excel(tmp_path, sheet_id=1, engine='xlsx2csv')
            except:
                try:
                    df = pl.read_excel(tmp_path, sheet_id=1, engine='openpyxl')
                except:
                    df = pl.read_excel(tmp_path)
        else:
            # Read CSV/TSV file
            df = pl.read_csv(tmp_path, separator='\t', infer_schema_length=10000)
        
        # Clean up temp file
        try:
            os.remove(tmp_path)
        except:
            pass
        
        headers = df.columns[1:] if len(df.columns) > 1 else []
        return {"columns": headers}
    except Exception as e:
        # Clean up temp file on error
        try:
            if 'tmp_path' in locals():
                os.remove(tmp_path)
        except:
            pass
        logger.error(f"Error previewing phenotype file: {e}")
        return {"error": f"Could not read file: {str(e)}"}, 500