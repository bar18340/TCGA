import PySimpleGUI as sg
import pandas as pd
from tcga.controller.controller import Controller
from tcga.utils.logger import setup_logger
import os

class GUI:
    def __init__(self, logger):
        """
        Initializes the GUI with the specified logger and sets up the layout.
        """
        self.logger = logger
        self.logger.info("Initializing GUI")
        self.controller = Controller(logger)  # Initialize Controller

        self.layout = [
            [sg.Text('TCGA - Data Merger Tool', font=('Helvetica', 16, 'bold'),
                     text_color='blue', justification='center', expand_x=True)],
            # Methylation File Selection
            [sg.Text('Methylation File:', size=(20, 1)),
             sg.Input(key='-MET_FILE-', enable_events=True, size=(45, 1)),
             sg.FileBrowse(button_text='Browse', tooltip='Select Methylation TSV File')],
            # Gene Mapping File Selection
            [sg.Text('Gene Mapping File:', size=(20, 1)),
             sg.Input(key='-GENE_MAP_FILE-', enable_events=True, size=(45, 1)),
             sg.FileBrowse(button_text='Browse', tooltip='Select Gene Mapping TSV File')],
            # Gene Expression File Selection
            [sg.Text('Gene Expression File:', size=(20, 1)),
             sg.Input(key='-GENE_EXP_FILE-', enable_events=True, size=(45, 1)),
             sg.FileBrowse(button_text='Browse', tooltip='Select Gene Expression TSV File')],
            # Phenotype File Selection
            [sg.Text('Phenotype File:', size=(20, 1)),
             sg.Input(key='-PHEN_FILE-', enable_events=True, size=(45, 1)),
             sg.FileBrowse(button_text='Browse', tooltip='Select Phenotype TSV File')],
            # Button to load phenotype characteristics
            [sg.Button('Load Phenotype Characteristics', key='-LOAD_PHEN-', button_color=('white', 'blue'))],
            # Listbox to display phenotype characteristics (hidden initially)
            [sg.Listbox(values=[], size=(45, 6), key='-PHEN_CHARS-', select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE, visible=False)],
            # Save Directory Selection
            [sg.Text('Save Directory:', size=(20, 1)),
             sg.Input(key='-SAVE_DIR-', enable_events=True, size=(45, 1)),
             sg.FolderBrowse(button_text='Browse', tooltip='Select Directory to Save CSV')],
            # Output File Name Input
            [sg.Text('Output File Name:', size=(20, 1)),
             sg.InputText('merged_data.csv', key='-OUTPUT_FILE-', size=(45, 1),
                          tooltip='Enter desired name for the CSV file')],
            # Maximum Percentage of Zeros Input
            [sg.Text('Clean rows with (%) of Zeros (0-100):', size=(30, 1)),
             sg.InputText('100', key='-ZERO_PERCENT-', size=(10, 1),
                          tooltip='Enter a number between 0 and 100')],
            # Action Buttons
            [sg.Button('Save Merged Data', size=(20, 1), button_color=('white', 'green')),
             sg.Button('Exit', size=(10, 1), button_color=('white', 'red'))],
            # Status Message
            [sg.Text('', size=(80, 3), key='-STATUS-', text_color='green',
                     font=('Helvetica', 10), expand_x=True)]
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
                        df = pd.read_csv(phen_file, sep='\t', encoding='utf-8')
                        # Get phenotype characteristics (skip the first column)
                        phen_chars = list(df.columns[1:])
                        self.window['-PHEN_CHARS-'].update(values=phen_chars, visible=True)
                        self.logger.info(f"Loaded phenotype characteristics: {phen_chars}")
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
        self.logger.info("Save Merged Data button clicked")
        methylation_path = values['-MET_FILE-']
        gene_mapping_path = values['-GENE_MAP_FILE-']
        gene_expression_path = values['-GENE_EXP_FILE-']
        phenotype_path = values['-PHEN_FILE-']
        selected_phenotypes = values['-PHEN_CHARS-'] if values['-PHEN_CHARS-'] else []
        save_dir = values['-SAVE_DIR-']
        output_file_name = values['-OUTPUT_FILE-'].strip()
        zero_percent = values['-ZERO_PERCENT-'].strip()

        # Determine scenario based on provided files
        is_methylation = bool(methylation_path)
        is_gene_mapping = bool(gene_mapping_path)
        is_gene_expression = bool(gene_expression_path)

        # Validate file combination
        if not ((is_gene_expression and not (is_methylation or is_gene_mapping)) or
                (is_methylation and is_gene_mapping and not is_gene_expression) or
                (is_methylation and is_gene_mapping and is_gene_expression)):
            sg.popup_error("Please select a valid combination of files:\n"
                           "1. Only Gene Expression File.\n"
                           "2. Methylation + Gene Mapping Files.\n"
                           "3. All Three Files (optionally with Phenotype).")
            self.logger.warning("Invalid combination of files selected.")
            self.update_status("Error: Invalid combination of files selected.", error=True)
            return

        try:
            zero_percent_value = float(zero_percent)
            if not (0 <= zero_percent_value <= 100):
                raise ValueError
        except ValueError:
            sg.popup_error("Maximum Percentage of Zeros must be a number between 0 and 100.")
            self.logger.warning("Invalid Maximum Percentage of Zeros input.")
            self.update_status("Error: Invalid Maximum Percentage of Zeros input.", error=True)
            return

        if not output_file_name.lower().endswith('.csv'):
            output_file_name += '.csv'
        if any(char in output_file_name for char in r'<>:"/\|?*'):
            sg.popup_error("The file name contains invalid characters. Please avoid <>:\"/\\|?*")
            self.logger.warning("Invalid characters found in Output File Name.")
            self.update_status("Error: Invalid characters in Output File Name.", error=True)
            return

        try:
            if is_gene_expression and not (is_methylation or is_gene_mapping):
                result = self.controller.process_files(
                    gene_expression_path=gene_expression_path,
                    phenotype_path=phenotype_path if phenotype_path else None,
                    selected_phenotypes=selected_phenotypes,
                    zero_percent=zero_percent_value
                )
                cleaned_df, rows_removed = result
                output_path = os.path.join(save_dir, output_file_name)
            elif is_methylation and is_gene_mapping and not is_gene_expression:
                result = self.controller.process_files(
                    methylation_path=methylation_path,
                    gene_mapping_path=gene_mapping_path,
                    phenotype_path=phenotype_path if phenotype_path else None,
                    selected_phenotypes=selected_phenotypes,
                    zero_percent=zero_percent_value
                )
                cleaned_df, rows_removed = result
                output_path = os.path.join(save_dir, output_file_name)
            elif is_methylation and is_gene_mapping and is_gene_expression:
                result = self.controller.process_files(
                    methylation_path=methylation_path,
                    gene_mapping_path=gene_mapping_path,
                    gene_expression_path=gene_expression_path,
                    phenotype_path=phenotype_path if phenotype_path else None,
                    selected_phenotypes=selected_phenotypes,
                    zero_percent=zero_percent_value
                )
                cleaned_meth_df, rows_removed_meth, cleaned_expr_df, rows_removed_expr = result
                meth_output_path = os.path.join(save_dir, 'merged_data.csv')
                counter = 1
                base_name, extension = os.path.splitext('merged_data.csv')
                while os.path.exists(meth_output_path):
                    meth_output_path = os.path.join(save_dir, f"{base_name}_{counter}{extension}")
                    counter += 1
                cleaned_meth_df.to_csv(meth_output_path, index=False)
                expr_output_path = os.path.join(save_dir, 'cleaned_gene_expression_data.csv')
                counter = 1
                base_name, extension = os.path.splitext('cleaned_gene_expression_data.csv')
                while os.path.exists(expr_output_path):
                    expr_output_path = os.path.join(save_dir, f"{base_name}_{counter}{extension}")
                    counter += 1
                cleaned_expr_df.to_csv(expr_output_path, index=False)
                status_message = (
                    f"Cleaned methylation data saved as '{os.path.basename(meth_output_path)}'.\n"
                    f"Removed {rows_removed_meth} methylation rows exceeding {zero_percent_value}% zeros.\n"
                    f"Cleaned gene expression data saved as '{os.path.basename(expr_output_path)}'.\n"
                    f"Removed {rows_removed_expr} gene expression rows exceeding {zero_percent_value}% zeros."
                )
                self.update_status(status_message, success=True)
                return

            if cleaned_df.empty:
                sg.popup_error("Cleaned DataFrame is empty. Please check the uploaded files.")
                self.logger.error("Cleaned DataFrame is empty.")
                self.update_status("Error: Cleaned DataFrame is empty.", error=True)
                return

            counter = 1
            base_name, extension = os.path.splitext(output_file_name)
            while os.path.exists(output_path):
                output_path = os.path.join(save_dir, f"{base_name}_{counter}{extension}")
                counter += 1

            cleaned_df.to_csv(output_path, index=False)
            self.logger.info(f"Cleaned data saved as '{os.path.basename(output_path)}' in '{save_dir}'.")
            final_file_name = os.path.basename(output_path)
            if rows_removed > 0:
                status_message = f"Cleaned data saved as '{final_file_name}'.\nRemoved {rows_removed} rows exceeding {zero_percent_value}% zeros."
            else:
                status_message = f"Cleaned data saved as '{final_file_name}'. No rows exceeded {zero_percent_value}% zeros."
            self.update_status(status_message, success=True)

        except ValueError as ve:
            sg.popup_error(f"Error processing files: {ve}\nPlease check the log for more details.")
            self.logger.error(f"Error processing files: {ve}")
            self.update_status(f"Error: {ve}", error=True)
        except Exception as e:
            sg.popup_error(f"An unexpected error occurred: {e}\nPlease check the log for more details.")
            self.logger.error(f"Unexpected error during processing: {e}")
            self.update_status(f"Error: {e}", error=True)

    def update_status(self, message, success=False, error=False):
        if success:
            self.window['-STATUS-'].update(message, text_color='black')
        elif error:
            self.window['-STATUS-'].update(message, text_color='red')
        else:
            self.window['-STATUS-'].update(message, text_color='black')
