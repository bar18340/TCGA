# tcga/interface/gui.py

import PySimpleGUI as sg
from tcga.data.file_handler import FileHandler
from tcga.utils.logger import setup_logger
import os

class GUI:
    def __init__(self, logger):
        self.logger = logger
        self.logger.info("Initializing GUI")
        self.file_handler = FileHandler(logger)  # Pass logger to FileHandler

        self.layout = [
            [sg.Text('TCGA - Data Merger Tool', font=('Helvetica', 16), justification='center', expand_x=True)],
            
            # Methylation File Selection
            [sg.Text('Methylation File:', size=(20, 1)), 
             sg.Input(key='-MET_FILE-', enable_events=True, size=(50,1)), 
             sg.FileBrowse()],
            
            # Gene Mapping File Selection
            [sg.Text('Gene Mapping File:', size=(20, 1)), 
             sg.Input(key='-GENE_MAP_FILE-', enable_events=True, size=(50,1)), 
             sg.FileBrowse()],
            
            # Save Directory Selection
            [sg.Text('Save Directory:', size=(20, 1)), 
             sg.Input(key='-SAVE_DIR-', enable_events=True, size=(50,1)), 
             sg.FolderBrowse()],
            
            # Action Buttons
            [sg.Button('Save Merged Data', size=(20, 1)), sg.Button('Exit', size=(10, 1))],
            
            # Status Message
            [sg.Text('', size=(80, 2), key='-STATUS-', text_color='green')]
        ]

        self.window = sg.Window('TCGA Data Merger', self.layout, finalize=True)

    def run(self):
        self.logger.info("Starting GUI event loop")
        while True:
            event, values = self.window.read()
            if event in (sg.WINDOW_CLOSED, 'Exit'):
                self.logger.info("Exiting GUI")
                break
            elif event == 'Save Merged Data':
                self.handle_save(values)
        self.window.close()
        self.logger.info("GUI window closed")
        self.file_handler.cleanup()

    def handle_save(self, values):
        self.logger.info("Save Merged Data button clicked")

        methylation_path = values['-MET_FILE-']
        gene_mapping_path = values['-GENE_MAP_FILE-']
        save_dir = values['-SAVE_DIR-']

        # Validate that all fields are selected
        if not methylation_path:
            sg.popup_error("Please select a Methylation File.")
            self.logger.warning("Methylation File not selected.")
            self.update_status("Error: Methylation File not selected.", error=True)
            return
        if not gene_mapping_path:
            sg.popup_error("Please select a Gene Mapping File.")
            self.logger.warning("Gene Mapping File not selected.")
            self.update_status("Error: Gene Mapping File not selected.", error=True)
            return
        if not save_dir:
            sg.popup_error("Please select a Save Directory.")
            self.logger.warning("Save Directory not selected.")
            self.update_status("Error: Save Directory not selected.", error=True)
            return

        try:
            # Upload both files
            methylation_file_name = self.file_handler.upload_file(methylation_path, 'methylation')
            gene_mapping_file_name = self.file_handler.upload_file(gene_mapping_path, 'gene_mapping')

            # Merge the files
            merged_df = self.file_handler.merge_files()

            if merged_df.empty:
                sg.popup_error("Merged DataFrame is empty. Please check the uploaded files.")
                self.logger.error("Merged DataFrame is empty.")
                self.update_status("Error: Merged DataFrame is empty.", error=True)
                return

            # Define merged file name
            merged_file_name = 'merged_methylation_data.csv'
            merged_file_path = os.path.join(save_dir, merged_file_name)

            # Handle duplicate file names
            counter = 1
            while os.path.exists(merged_file_path):
                merged_file_name = f'merged_methylation_data_{counter}.csv'
                merged_file_path = os.path.join(save_dir, merged_file_name)
                counter += 1

            # Save merged DataFrame as CSV
            merged_df.to_csv(merged_file_path, index=False)
            self.logger.info(f"Merged data saved as '{merged_file_name}' in '{save_dir}'.")

            # Update status in GUI
            self.update_status(f"Merged data saved as '{merged_file_name}'.", success=True)

        except ValueError as ve:
            sg.popup_error(f"Error merging files: {ve}")
            self.logger.error(f"Error merging files: {ve}")
            self.update_status(f"Error: {ve}", error=True)
        except Exception as e:
            sg.popup_error(f"An unexpected error occurred: {e}")
            self.logger.error(f"Unexpected error during merging: {e}")
            self.update_status(f"Error: {e}", error=True)

    def update_status(self, message, success=False, error=False):
        """
        Updates the status message in the GUI.

        Parameters:
            message (str): The message to display.
            success (bool): If True, displays the message in green.
            error (bool): If True, displays the message in red.
        """
        if success:
            self.window['-STATUS-'].update(message, text_color='black')
        elif error:
            self.window['-STATUS-'].update(message, text_color='red')
        else:
            self.window['-STATUS-'].update(message)
