import PySimpleGUI as sg
import os
import polars as pl
import time
from tcga.controller.controller import Controller
from tcga.utils.logger import setup_logger

class GUI:
    def __init__(self, logger):
        self.logger = logger
        self.controller = Controller(logger)

        # Optional: use a modern theme
        sg.theme("LightGrey5")

        # ---------- Input Files Section ----------
        input_frame = sg.Frame("🧬 Input Files", [
            [sg.Text('Methylation File:', size=(18, 1)),
             sg.Input(key='-MET_FILE-', enable_events=True, size=(50, 1)),
             sg.FileBrowse('Browse')],
            [sg.Text('Gene Mapping File:', size=(18, 1)),
             sg.Input(key='-GENE_MAP_FILE-', enable_events=True, size=(50, 1)),
             sg.FileBrowse('Browse')],
            [sg.Text('Gene Expression File:', size=(18, 1)),
             sg.Input(key='-GENE_EXP_FILE-', enable_events=True, size=(50, 1)),
             sg.FileBrowse('Browse')],
            [sg.Text('Phenotype File:', size=(18, 1)),
             sg.Input(key='-PHEN_FILE-', enable_events=True, size=(50, 1)),
             sg.FileBrowse('Browse')],
            [sg.Button('Load Phenotype Characteristics', key='-LOAD_PHEN-', button_color=('white', 'blue'))],
            [sg.Listbox(values=[], size=(60, 5), key='-PHEN_CHARS-', select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE, visible=False)]
        ], pad=(10, 10))

        # ---------- Output Settings Section ----------
        output_frame = sg.Frame("💾 Output Settings", [
            [sg.Text('Save Directory:', size=(18, 1)),
             sg.Input(key='-SAVE_DIR-', size=(50, 1)),
             sg.FolderBrowse('Browse')],
            [sg.Text('Output File Name:', size=(18, 1)),
             sg.InputText('merged_data.csv', key='-OUTPUT_FILE-', size=(50, 1))],
            [sg.Text('Clean rows with (%) of Zeros:', size=(30, 1)),
             sg.InputText('100', key='-ZERO_PERCENT-', size=(6, 1))]
        ], pad=(10, 10))

        # ---------- Action Buttons and Status ----------
        action_row = [
            sg.Button('Save Merged Data', size=(20, 1), button_color=('white', 'green')),
            sg.Button('Exit', size=(10, 1), button_color=('white', 'red'))
        ]

        status_row = [
            sg.Text('', size=(80, 3), key='-STATUS-', text_color='green', font=('Segoe UI', 10), expand_x=True)
        ]

        # ---------- Assemble the full layout ----------
        self.layout = [
            [sg.Text('🧪 TCGA Data Merger Tool', font=('Helvetica', 18, 'bold'),
                     justification='center', expand_x=True, text_color='black')],
            [input_frame],
            [output_frame],
            [sg.HSeparator()],
            action_row,
            status_row
        ]

        self.window = sg.Window('TCGA Data Merger', self.layout, finalize=True, resizable=True)

    def run(self):
        self.logger.info("Starting GUI event loop")
        while True:
            event, values = self.window.read()
            if event in (sg.WINDOW_CLOSED, 'Exit'):
                self.logger.info("Exiting GUI")
                break

            elif event == '-LOAD_PHEN-':
                phen_file = values['-PHEN_FILE-']
                if phen_file:
                    try:
                        df = pl.read_csv(phen_file, separator='\t', infer_schema_length=10000)
                        characteristics = self.controller.phenotype_processor.get_characteristics(df)
                        self.window['-PHEN_CHARS-'].update(values=characteristics, visible=True)
                        self.logger.info(f"Loaded phenotype characteristics: {characteristics}")
                    except Exception as e:
                        sg.popup_error(f"Error loading phenotype file: {e}")
                        self.logger.error(f"Error loading phenotype file: {e}")
                else:
                    sg.popup_error("Please select a phenotype file first.")

            elif event == 'Save Merged Data':
                self.handle_save(values)

        self.window.close()
        self.logger.info("GUI window closed")
        self.controller.file_handler.cleanup()

    def handle_save(self, values):
        start = time.time()

        self.logger.info("Save Merged Data button clicked")
        methylation_path = values['-MET_FILE-']
        gene_mapping_path = values['-GENE_MAP_FILE-']
        gene_expression_path = values['-GENE_EXP_FILE-']
        phenotype_path = values['-PHEN_FILE-']
        selected_phenotypes = values['-PHEN_CHARS-'] if values['-PHEN_CHARS-'] else []
        save_dir = values['-SAVE_DIR-']
        output_file_name = values['-OUTPUT_FILE-'].strip()
        zero_percent = values['-ZERO_PERCENT-'].strip()

        # Validate % of zeros
        try:
            zero_percent_value = float(zero_percent)
            if not (0 <= zero_percent_value <= 100):
                raise ValueError
        except ValueError:
            sg.popup_error("Maximum Percentage of Zeros must be a number between 0 and 100.")
            self.logger.warning("Invalid zero percent input.")
            self.update_status("Error: Invalid zero percent input.", error=True)
            return

        if not output_file_name:
            output_file_name = "merged_data.csv"

        base_name = os.path.splitext(output_file_name)[0]  # strip any extension
        csv_name1 = f"{base_name}_methylation.csv"
        csv_name2 = f"{base_name}_expression.csv"

        try:
            result = self.controller.process_files(
                methylation_path=methylation_path if methylation_path else None,
                gene_mapping_path=gene_mapping_path if gene_mapping_path else None,
                gene_expression_path=gene_expression_path if gene_expression_path else None,
                phenotype_path=phenotype_path if phenotype_path else None,
                selected_phenotypes=selected_phenotypes,
                zero_percent=zero_percent_value
            )

            df1, _, df2, _ = result if len(result) == 4 else (*result, None, None)

            # Build output paths
            csv_path1 = os.path.join(save_dir, csv_name1)
            csv_path2 = os.path.join(save_dir, csv_name2)

            counter = 1
            while os.path.exists(csv_path1):
                csv_path1 = os.path.join(save_dir, f"{base_name}_methylation_{counter}.csv")
                counter += 1

            counter = 1
            while df2 is not None and os.path.exists(csv_path2):
                csv_path2 = os.path.join(save_dir, f"{base_name}_expression_{counter}.csv")
                counter += 1

            if df1 is not None:
                df1.write_csv(csv_path1)

            if df2 is not None:
                df2.write_csv(csv_path2)

            end = time.time()
            elapsed = end - start

            message = f"CSV file saved: {os.path.basename(csv_path1)}"
            if df2 is not None:
                message += f"\nCSV file saved: {os.path.basename(csv_path2)}"
            message += f"\nProcessing time: {elapsed:.2f} seconds"
                
            self.update_status(message, success=True)

        except Exception as e:
            sg.popup_error(f"Error: {e}")
            self.logger.error(f"Unexpected error: {e}")
            self.update_status(str(e), error=True)


    def update_status(self, message, success=False, error=False):
        if success:
            self.window['-STATUS-'].update(message, text_color='black')
        elif error:
            self.window['-STATUS-'].update(message, text_color='red')
        else:
            self.window['-STATUS-'].update(message, text_color='black')
