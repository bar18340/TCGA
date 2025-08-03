# 🧬 TCGA Data Merger Tool

A powerful, modern Python application for processing and merging TCGA (The Cancer Genome Atlas) genomic data files through an intuitive desktop interface. Features drag-and-drop file uploads, real-time validation, and optimized data processing for research workflows.
Built with Polars for high-performance data processing
UI powered by Flask and modern web technologies
Desktop integration via PyWebView

## ✨ Key Features

### 🎯 Modern User Interface
- **Drag & Drop Support** - Simply drag your data files into the upload zones
- **Real-time Validation** - Instant feedback on file combinations and requirements
- **Visual Progress Tracking** - Animated progress bars and loading indicators
- **Smart Format Selection** - Automatic optimization for large files (CSV vs Excel)
- **Toast Notifications** - Clear, non-intrusive status updates

### 📊 Data Processing Capabilities
- **Multi-format Support** - Process CSV, TSV, and Excel files seamlessly
- **Intelligent Gene Matching** - Automatically align genes across methylation and expression data
- **Flexible Filtering** - Remove rows based on zero-value thresholds (0-100%)
- **Phenotype Integration** - Dynamically preview and select phenotype characteristics
- **Batch Processing** - Handle multiple large files efficiently

### 🔧 Technical Features
- **100% Offline** - No internet required, your data stays private
- **Cross-file Validation** - Ensures proper file combinations (methylation + mapping, etc.)
- **Memory Efficient** - Handles large genomic datasets without freezing
- **Export Options** - Save as CSV (recommended) or Excel format
- **Desktop Integration** - Native folder picker for easy file management

## 🚀 Quick Start (For End Users)

1. **Download** the latest release from GitHub
2. **Extract** the ZIP file to any location on your computer
3. **Double-click** the '.exe' file to launch
4. **Drag and drop** your files or click to browse
5. **Configure** your output settings
6. **Process** and save your merged data!

### System Requirements
- Windows 10/11 (64-bit)
- 4GB RAM minimum (8GB recommended for large datasets)
- Microsoft Edge WebView2 Runtime (usually pre-installed)

## 📁 Supported File Combinations

| Files Required | Description |
|---------------|-------------|
| Methylation + Gene Mapping | Process methylation data with gene annotations |
| Methylation + Gene Mapping + Expression | Merge all three data types |
| Methylation + Gene Mapping + Phenotype | Add clinical data to methylation |
| Expression Only | Process gene expression independently |
| Expression + Phenotype | Combine expression with clinical data |
| All Four Files | Complete integrated analysis |

## 🛠️ Developer Setup

### Prerequisites
- Python 3.8 or higher
- Git
- Visual Studio Code (recommended)

### Installation

```bash
cd TCGA

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
Running from Source
bash# Launch the desktop application
python gui_launcher.py
```

# 📝 File Format Requirements

## Methylation Files:

Tab-separated values
First column: Gene/Probe IDs
Subsequent columns: Patient data

## Gene Mapping Files:

Two columns minimum
Column 1: Gene/Probe IDs (matching methylation)
Column 2: Actual gene names

## Expression Files:

First column: Gene names
Subsequent columns: Expression values per patient

## Phenotype Files:

First column: Patient IDs
Subsequent columns: Clinical characteristics

# 📊 Performance Tips

Large files (>50MB): Use CSV format for faster processing
Memory usage: Close other applications when processing very large datasets
Optimal threshold: Start with 100% zero threshold, adjust based on your data

# 🐛 Troubleshooting:

## Application won't start:

Install Microsoft Edge WebView2 Runtime
Run as Administrator if permission errors occur
Check Windows Defender hasn't blocked the executable

## File processing errors:

Ensure file formats match the requirements above
Check that methylation files have corresponding mapping files
Verify patient IDs match across files