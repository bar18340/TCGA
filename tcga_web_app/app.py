import os
import uuid
import shutil
import polars as pl
from flask import Flask, render_template, request, redirect, send_file, flash, url_for
from tcga.controller.controller import Controller
from tcga.utils.logger import setup_logger

# --- Flask App Config ---
app = Flask(__name__)
app.secret_key = 'tcga_secret_key'
UPLOAD_FOLDER = 'tcga_web_app/uploads'
OUTPUT_FOLDER = 'tcga_web_app/outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- Use existing TCGA controller logic ---
logger = setup_logger()
controller = Controller(logger=logger)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # --- Handle uploaded files ---
            methylation_file = request.files.get('methylation_file')
            mapping_file = request.files.get('mapping_file')
            expression_file = request.files.get('expression_file')
            phenotype_file = request.files.get('phenotype_file')
            zero_threshold = float(request.form.get('zero_threshold', 100))
            selected_phenos = request.form.getlist('phenos')  # Placeholder for future dynamic UI

            # --- Save uploaded files ---
            file_paths = {}
            for label, file in {
                'methylation': methylation_file,
                'gene_mapping': mapping_file,
                'gene_expression': expression_file,
                'phenotype': phenotype_file
            }.items():
                if file and file.filename:
                    save_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{file.filename}")
                    file.save(save_path)
                    file_paths[label] = save_path

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
            df1, _, df2, _ = result if len(result) == 4 else (*result, None, None)
            output_paths = []

            if df1 is not None:
                out1 = os.path.join(OUTPUT_FOLDER, "methylation_output.csv")
                df1.write_csv(out1)
                output_paths.append(url_for('download_file', filename='methylation_output.csv'))

            if df2 is not None:
                out2 = os.path.join(OUTPUT_FOLDER, "expression_output.csv")
                df2.write_csv(out2)
                output_paths.append(url_for('download_file', filename='expression_output.csv'))

            return render_template('index.html', success=True, outputs=output_paths)

        except Exception as e:
            flash(f"❌ Error: {e}", 'error')
            return redirect('/')

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.abspath(os.path.join(OUTPUT_FOLDER, filename))
    if not os.path.exists(filepath):
        return f"❌ File not found: {filename}", 404
    return send_file(filepath, as_attachment=True)


@app.route('/reset')
def reset():
    shutil.rmtree(UPLOAD_FOLDER, ignore_errors=True)
    shutil.rmtree(OUTPUT_FOLDER, ignore_errors=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    flash("App has been reset.", 'info')
    return redirect('/')

@app.route('/preview_phenotype', methods=['POST'])
def preview_phenotype():
    file = request.files.get('phenotype_file')
    if not file:
        return {"error": "No file uploaded"}, 400

    try:
        import polars as pl
        df = pl.read_csv(file, separator='\t', infer_schema_length=10000)
        headers = df.columns[1:]  # Skip patient ID column
        return {"columns": headers}
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True)
