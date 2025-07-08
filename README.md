# 🧬 TCGA Data Merger Tool

A fast, modular Python tool that helps researchers clean and merge TCGA data files locally through a user-friendly web interface.
Supports methylation data, gene mapping, gene expression, and phenotype information — and outputs clean, aligned `.csv` files.

## ⚙️ Features
✅ Upload multiple types of files  
✅ Auto-match genes across files  
✅ Remove genes/rows based on % of zeros  
✅ Add phenotype characteristics dynamically  
✅ Save cleaned data as `.csv`  
✅ Runs entirely offline

## 🚀 Usage (for End-Users)
1.  Download the latest release
2.  Unzip the folder to a location on your PC.
3.  Double-click the **`tcga.exe`** to launch the application.

## 🛠️ Developer Setup
To run the application from the source code:
Clone the repository and install the required dependencies.
```bash
# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate # On Windows
# Install dependencies
pip install -r requirements.txt
```
### Running the Application
Launch the app using the `gui_launcher.py` script.
```bash
python gui_launcher.py
```
### Running Tests
The project includes a comprehensive test suite. To run the tests:
```bash
pip install pytest pytest-mock
pytest
```
