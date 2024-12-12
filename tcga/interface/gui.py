# tcga/interface/gui.py

import PySimpleGUI as sg
from tcga.controller.controller import Controller
from tcga.utils.logger import setup_logger
import os

class GUI:
    def __init__(self, logger):
        """
        Initializes the GUI with the specified logger and sets up the layout.

        Parameters:
            logger (logging.Logger): The logger instance for logging events.
        """
        self.logger = logger
        self.logger.info("Initializing GUI")
        self.controller = Controller(logger)  # Initialize Controller

        self.layout = [
            [sg.Text('TCGA - Data Merger Tool', font=('Helvetica', 16, 'bold'), text_color='blue', justification='center', expand_x=True)],
            
            # Methylation File Selection
            [sg.Text('Methylation File:', size=(20, 1)), 
             sg.Input(key='-MET_FILE-', enable_events=True, size=(45,1)), 
             sg.FileBrowse(button_text='Browse', tooltip='Select Methylation TSV File')],
            
            # Gene Mapping File Selection
            [sg.Text('Gene Mapping File:', size=(20, 1)), 
             sg.Input(key='-GENE_MAP_FILE-', enable_events=True, size=(45,1)), 
             sg.FileBrowse(button_text='Browse', tooltip='Select Gene Mapping TSV File')],
            
            # Save Directory Selection
            [sg.Text('Save Directory:', size=(20, 1)), 
             sg.Input(key='-SAVE_DIR-', enable_events=True, size=(45,1)), 
             sg.FolderBrowse(button_text='Browse', tooltip='Select Directory to Save Merged CSV')],
            
            # Output File Name Input
            [sg.Text('Output File Name:', size=(20, 1)), 
             sg.InputText('merged_methylation_data.csv', key='-OUTPUT_FILE-', size=(45,1), tooltip='Enter desired name for the merged CSV file')],
            
            # Maximum Percentage of Zeros Input
            [sg.Text('Clean rows with (%) of Zeros (0-100):', size=(30,1)),
             sg.InputText('100', key='-ZERO_PERCENT-', size=(10,1), tooltip='Enter a number between 0 and 100')],
            
            # Action Buttons
            [sg.Button('Save Merged Data', size=(20, 1), button_color=('white', 'green')),
             sg.Button('Exit', size=(10, 1), button_color=('white', 'red'))],
            
            # Status Message
            [sg.Text('', size=(80, 3), key='-STATUS-', text_color='green', font=('Helvetica', 10), expand_x=True)]
        ]

        self.window = sg.Window('TCGA Data Merger', self.layout, finalize=True, resizable=True)

    def run(self):
        """
        Starts the GUI event loop, handling user interactions.
        """
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
        self.controller.file_handler.cleanup()

    def handle_save(self, values):
        """
        Handles the 'Save Merged Data' button click event. Validates inputs,
        uploads files, processes data, and saves the output.

        Parameters:
            values (dict): Dictionary containing the current values of the GUI elements.
        """
        self.logger.info("Save Merged Data button clicked")

        methylation_path = values['-MET_FILE-']
        gene_mapping_path = values['-GENE_MAP_FILE-']
        save_dir = values['-SAVE_DIR-']
        output_file_name = values['-OUTPUT_FILE-'].strip()
        zero_percent = values['-ZERO_PERCENT-'].strip()

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
        if not output_file_name:
            sg.popup_error("Please enter a name for the output file.")
            self.logger.warning("Output File Name not provided.")
            self.update_status("Error: Output File Name not provided.", error=True)
            return
        if not zero_percent:
            sg.popup_error("Please enter the Maximum Percentage of Zeros.")
            self.logger.warning("Maximum Percentage of Zeros not provided.")
            self.update_status("Error: Maximum Percentage of Zeros not provided.", error=True)
            return

        # Validate the zero_percent input
        try:
            zero_percent_value = float(zero_percent)
            if not (0 <= zero_percent_value <= 100):
                raise ValueError
        except ValueError:
            sg.popup_error("Maximum Percentage of Zeros must be a number between 0 and 100.")
            self.logger.warning("Invalid Maximum Percentage of Zeros input.")
            self.update_status("Error: Invalid Maximum Percentage of Zeros input.", error=True)
            return

        # Ensure the file name has a .csv extension
        if not output_file_name.lower().endswith('.csv'):
            output_file_name += '.csv'

        # Validate the file name for illegal characters
        if any(char in output_file_name for char in r'<>:"/\|?*'):
            sg.popup_error("The file name contains invalid characters. Please avoid <>:\"/\\|?*")
            self.logger.warning("Invalid characters found in Output File Name.")
            self.update_status("Error: Invalid characters in Output File Name.", error=True)
            return

        try:
            # Process files using the Controller
            cleaned_df, rows_removed = self.controller.process_files(
                methylation_path=methylation_path,
                gene_mapping_path=gene_mapping_path,
                zero_percent=zero_percent_value
            )

            if cleaned_df.empty:
                sg.popup_error("Merged DataFrame is empty. Please check the uploaded files.")
                self.logger.error("Merged DataFrame is empty.")
                self.update_status("Error: Merged DataFrame is empty.", error=True)
                return

            # Define merged file path
            merged_file_path = os.path.join(save_dir, output_file_name)

            # Handle duplicate file names by appending a counter
            counter = 1
            base_name, extension = os.path.splitext(output_file_name)
            while os.path.exists(merged_file_path):
                merged_file_name = f"{base_name}_{counter}{extension}"
                merged_file_path = os.path.join(save_dir, merged_file_name)
                counter += 1

            # Save merged DataFrame as CSV
            cleaned_df.to_csv(merged_file_path, index=False)
            self.logger.info(f"Merged data saved as '{os.path.basename(merged_file_path)}' in '{save_dir}'.")

            # Determine the final file name (with counter if appended)
            final_file_name = os.path.basename(merged_file_path)

            # Update status in GUI with rows removed
            if rows_removed > 0:
                status_message = f"Merged data saved as '{final_file_name}'.\nRemoved {rows_removed} rows exceeding {zero_percent_value}% zeros."
            else:
                status_message = f"Merged data saved as '{final_file_name}'. No rows exceeded {zero_percent_value}% zeros."
            self.update_status(status_message, success=True)

        except ValueError as ve:
            sg.popup_error(f"Error merging files: {ve}\nPlease check the log for more details.")
            self.logger.error(f"Error merging files: {ve}")
            self.update_status(f"Error: {ve}", error=True)
        except Exception as e:
            sg.popup_error(f"An unexpected error occurred: {e}\nPlease check the log for more details.")
            self.logger.error(f"Unexpected error during merging: {e}")
            self.update_status(f"Error: {e}", error=True)

    def update_status(self, message, success=False, error=False):
        """
        Updates the status message in the GUI.

        Parameters:
            message (str): The message to display.
            success (bool): If True, displays the message in black.
            error (bool): If True, displays the message in red.
        """
        if success:
            self.window['-STATUS-'].update(message, text_color='black')
        elif error:
            self.window['-STATUS-'].update(message, text_color='red')
        else:
            self.window['-STATUS-'].update(message)
