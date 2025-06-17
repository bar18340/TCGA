# 🧬 TCGA Data Merger Tool

A fast, modular Python tool that helps researchers clean and merge TCGA data files locally through a user-friendly web interface.
Supports methylation data, gene mapping, gene expression, and phenotype information — and outputs clean, aligned `.csv` files.

## 📁 Project Structure
TCGA/
│
├── tcga/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── interface/
│   │   ├── __init__.py
│   │   └── gui.py
│   │
│   ├── controller/
│   │   ├── __init__.py
│   │   └── controller.py
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── file_handler.py
│   │   ├── data_cleaner.py
│   │   ├── data_merger.py
│   │   └── data_phenotype.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py
│
├── tcga_web_app/
│   ├── app.py
│   ├── templates/index.html
│   └── static/style.css
│
├── README.md
│
└── requirements.txt

## ⚙️ Features
✅ Upload multiple types of files  
✅ Auto-match genes across files  
✅ Remove genes/rows based on % of zeros  
✅ Add phenotype characteristics dynamically  
✅ Save cleaned data as `.csv`  
✅ Runs entirely offline

## 🚀 Run the App (Developer Mode)
### 1. Install dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

### 2. Launch App
python gui_launcher.py
