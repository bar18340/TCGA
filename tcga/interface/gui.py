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
            [sg.Text('TCGA - Data Merger Tool', font=('Helvetica', 16))],
            [sg.Button('Upload Methylation File'), sg.Button('Upload Gene Mapping File')],
            [sg.Text('Uploaded Methylation Files:')],
            [sg.Listbox(values=[], size=(80, 5), key='-MET FILE LIST-')],
            [sg.Text('Uploaded Gene Mapping Files:')],
            [sg.Listbox(values=[], size=(80, 5), key='-GENE MAP FILE LIST-')],
            [sg.Button('Save Merged Data'), sg.Button('Exit')]
        ]
        self.window = sg.Window('TCGA', self.layout, finalize=True)

    def run(self):
        self.logger.info("Starting GUI event loop")
        while True:
            event, values = self.window.read()
            if event in (sg.WINDOW_CLOSED, 'Exit'):
                self.logger.info("Exiting GUI")
                break
            elif event == 'Upload Methylation File':
                self.handle_upload('methylation')
            elif event == 'Upload Gene Mapping File':
                self.handle_upload('gene_mapping')
            elif event == 'Save Merged Data':
                self.handle_save()
        self.window.close()
        self.logger.info("GUI window closed")
        self.file_handler.cleanup()

    def handle_upload(self, file_type):
        if file_type == 'methylation':
            listbox_key = '-MET FILE LIST-'
            button_label = 'Upload Methylation File'
        elif file_type == 'gene_mapping':
            listbox_key = '-GENE MAP FILE LIST-'
            button_label = 'Upload Gene Mapping File'
        else:
            self.logger.error(f"Unknown file type: {file_type}")
            return

        self.logger.info(f"{button_label} button clicked")
        file_paths = sg.popup_get_file(
            f'Select {file_type.capitalize()} Files to Upload', 
            multiple_files=True, 
            file_types=[("All Files", "*.*")],  # Allow any file type
            title=f"Upload {file_type.capitalize()} Files"
        )
        if file_paths:
            # Split the file paths based on the operating system
            if ';' in file_paths:
                files = file_paths.split(';')
            elif '|' in file_paths:
                files = file_paths.split('|')
            else:
                files = [file_paths]
            
            for file_path in files:
                try:
                    file_name = self.file_handler.upload_file(file_path, file_type)
                    current_files = self.window[listbox_key].get_list_values()
                    self.window[listbox_key].update(values=current_files + [file_name])
                    
                    # Retrieve the DataFrame and create a preview string
                    df = self.file_handler.get_file(file_type, file_name)
                    if df is not None:
                        preview = df.head().to_string(index=False)
                        sg.popup_scrolled(f"Preview of '{file_name}':\n\n{preview}", title=f"Preview - {file_name}", size=(80, 20))
                    else:
                        self.logger.warning(f"No DataFrame found for '{file_name}'.")
                        sg.popup_error(f"No data found in '{file_name}'.")
                    
                except ValueError as ve:
                    sg.popup_error(f"Error uploading '{file_path}': {ve}")
                    self.logger.error(f"Error uploading '{file_path}': {ve}")

    def handle_save(self):
        self.logger.info("Save Merged Data button clicked")
        try:
            merged_df = self.file_handler.merge_files()
            if merged_df.empty:
                sg.popup_error("Merged DataFrame is empty. Ensure both files are uploaded correctly.")
                self.logger.error("Merged DataFrame is empty.")
                return
        except ValueError as ve:
            sg.popup_error(f"Error merging files: {ve}")
            self.logger.error(f"Error merging files: {ve}")
            return
        except Exception as e:
            sg.popup_error(f"An unexpected error occurred during merging: {e}")
            self.logger.error(f"Unexpected error during merging: {e}")
            return

        output_dir = sg.popup_get_folder('Select Folder to Save Merged CSV File', title="Save Merged CSV")
        if output_dir:
            try:
                merged_file_name = 'merged_methylation_data.csv'
                merged_file_path = os.path.join(output_dir, merged_file_name)
                # Handle duplicate file names
                counter = 1
                while os.path.exists(merged_file_path):
                    merged_file_name = f'merged_methylation_data_{counter}.csv'
                    merged_file_path = os.path.join(output_dir, merged_file_name)
                    counter += 1
                merged_df.to_csv(merged_file_path, index=False)
                sg.popup(f"Merged data has been saved as '{merged_file_name}' in '{output_dir}'.", title='Save Successful')
                self.logger.info(f"Merged data saved as '{merged_file_name}' in '{output_dir}'.")
            except Exception as e:
                sg.popup_error(f"Error saving merged data: {e}")
                self.logger.error(f"Error saving merged data: {e}")
        else:
            self.logger.info("Save Merged Data operation cancelled by the user.")
