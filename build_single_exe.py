"""
Build script for creating a single executable file with distribution package
"""
import PyInstaller.__main__
import os
import shutil
import zipfile
from datetime import datetime

def create_readme_content():
    """Generate the enhanced README content"""
    return """Data Merger Tool
=====================

## 🚀 Quick Start

1. **Extract the ZIP file** to any folder on your PC.

2. **Double-click `Data_Merger_Tool.exe`** to launch the tool.
   • No installation needed — runs entirely offline on your computer
   • If Windows shows "Unknown Publisher," click "More info" → "Run anyway"
   • First launch may take 10-30 seconds to start

3. **IMPORTANT:** Extract the **entire** folder first — don't run the EXE directly from inside the ZIP.

---

## 📊 Input File Structure & Formats

### Supported File Formats
- **Excel:** `.xlsx`, `.xls` (recommended for special characters)
- **CSV:** `.csv` (comma-separated)
- **TSV:** `.tsv`, `.txt` (tab-separated)
- **File Size:** Files >50MB will automatically use CSV output for performance

### Required File Structures

After launch, you can upload files via drag-and-drop or browse buttons:

#### 1️⃣ **Gene Expression File** (Optional)
| Gene_ID | patient_001 | patient_002 | patient_003 | … |
| ------- | ----------- | ----------- | ----------- | - |
| BRCA1   | 12.3        | 8.9         | 14.5        | … |
| TP53    | 5.6         | 7.1         | 6.2         | … |
| EGFR    | 9.8         | 10.4        | 8.3         | … |
| …       | …           | …           | …           | … |

**Notes:**
- First column: Gene names (must match mapping file if used together)
- Other columns: Patient IDs (must match across files)
- Values: Expression levels (typically log-transformed)

#### 2️⃣ **Methylation File** (Requires Gene Mapping)
| Probe_ID   | patient_001 | patient_002 | patient_003 | … |
| ---------- | ----------- | ----------- | ----------- | - |
| cg00000029 | 0.12        | 0.15        | 0.10        | … |
| cg00000108 | 0.45        | 0.39        | 0.42        | … |
| cg00000109 | 0.22        | 0.18        | 0.25        | … |
| …          | …           | …           | …           | … |

**Notes:**
- First column: Probe/CpG identifiers
- Other columns: Patient IDs (must match expression file if used)
- Values: Beta values (0-1 range)
- Missing values (NA, null) → converted to 0.0

#### 3️⃣ **Gene Mapping File** (Required with Methylation)
| Probe_ID   | Gene_ID        | … |
| ---------- | -------------- | - |
| cg00000029 | BRCA1          | … |
| cg00000108 | TP53           | … |
| cg00000109 | EGFR,EGFR-AS1  | … |
| …          | …              | … |

**Notes:**
- Column 1: Same probe IDs as methylation file
- Column 2: Gene names (can be comma-separated for multiple mappings)
- Genes marked as "." will be removed
- Extra columns ignored

#### 4️⃣ **Phenotype File** (Optional)
| Patient_ID  | Age | Sex | Tumor_Stage | Treatment_Response | … |
| ----------- | --- | --- | ----------- | ------------------ | - |
| patient_001 | 57  | F   | II          | Responder          | … |
| patient_002 | 63  | M   | III         | Non-responder      | … |
| patient_003 | 48  | F   | I           | Responder          | … |
| …           | …   | …   | …           | …                  | … |

**Notes:**
- First column: Patient IDs (must match other files exactly)
- Other columns: Any clinical/demographic data
- Selected characteristics will be added as rows at TOP of output
- Missing phenotype values appear as empty strings

---

## ⚙️ Processing Options

### Zero Threshold Filter
- **Purpose:** Remove rows with too many zero values
- **0%** = Keep only rows with NO zeros (strictest)
- **50%** = Remove rows with ≥50% zeros
- **100%** = Keep all rows (default, no filtering)

### Output Format Selection
- **CSV:** Faster processing, smaller files, better for large datasets
- **Excel:** Easier to open, better for small datasets (<50MB)
- **Auto-switch:** Files >50MB automatically use CSV format

---

## 📁 Output Files

### Location & Naming
- Choose output folder via the interface
- Files auto-named with unique suffixes to prevent overwrites:
  - `[your_name]_methylation.csv`
  - `[your_name]_expression.csv`
  - If files exist: `_1`, `_2`, etc. added automatically

### Output Structure
- **Methylation output:** Gene_Code | Actual_Gene_Name | Patient_Data...
- **Expression output:** Gene_Name | Patient_Data...
- **With phenotype:** Selected characteristics appear as first rows
- **Only common patients and genes** are included in output

---

## ✅ Valid File Combinations & Outcomes

| #  | Methylation | Gene Mapping | Gene Expression | Phenotype | Outcome                                                                           |
|----|-------------|--------------|-----------------|-----------|-----------------------------------------------------------------------------------|
| 1  | ❌          | ❌           | ❌              | ❌        | **Invalid:** No files provided                                                    |
| 2  | ❌          | ❌           | ❌              | ✅        | **Invalid:** Phenotype alone → nothing to merge with                              |
| 3  | ❌          | ❌           | ✅              | ❌        | **Valid:** Process gene expression only                                           |
| 4  | ❌          | ❌           | ✅              | ✅        | **Valid:** Process expression + append phenotype rows                             |
| 5  | ❌          | ✅           | ❌              | ❌        | **Invalid:** Mapping alone → needs methylation data                               |
| 6  | ❌          | ✅           | ❌              | ✅        | **Invalid:** Mapping + phenotype → needs methylation                              |
| 7  | ❌          | ✅           | ✅              | ❌        | **Invalid:** Mapping + expression → mapping only applies to methylation           |
| 8  | ❌          | ✅           | ✅              | ✅        | **Invalid:** Mapping + expression + phenotype → needs methylation                 |
| 9  | ✅          | ❌           | ❌              | ❌        | **Invalid:** Methylation alone → needs gene mapping file                          |
| 10 | ✅          | ❌           | ❌              | ✅        | **Invalid:** Methylation + phenotype → needs mapping to interpret probes          |
| 11 | ✅          | ❌           | ✅              | ❌        | **Invalid:** Methylation + expression → needs mapping for methylation             |
| 12 | ✅          | ❌           | ✅              | ✅        | **Invalid:** Methylation + expression + phenotype → needs mapping                 |
| 13 | ✅          | ✅           | ❌              | ❌        | **Valid:** Map probes to genes in methylation data                                |
| 14 | ✅          | ✅           | ❌              | ✅        | **Valid:** Map methylation + append phenotype rows                                |
| 15 | ✅          | ✅           | ✅              | ❌        | **Valid:** Merge both, keep only mutual patients & genes                          |
| 16 | ✅          | ✅           | ✅              | ✅        | **Valid:** Full integration with clinical data                                    |

---

## 🔧 Troubleshooting

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| **App won't start** | • Install Visual C++ Redistributable (x64): https://aka.ms/vs/17/release/vc_redist.x64.exe<br>• Run as Administrator (right-click → Run as administrator) |
| **"Could not launch native window"** | Install Microsoft Edge WebView2 Runtime: https://developer.microsoft.com/en-us/Microsoft-edge/webview2/ |
| **Slow startup** | First run takes 10-30 seconds. Subsequent runs are faster. |
| **"No common patients found"** | Check patient IDs match EXACTLY across files (case-sensitive) |
| **"No common genes found"** | Verify gene names in mapping match those in expression file |
| **Phenotype preview not showing** | Use Excel format (.xlsx) for phenotype files instead of CSV |
| **Processing takes forever** | Use CSV output format for files >50MB |
| **Windows Defender warning** | Click "More info" → "Run anyway" (file is safe but unsigned) |

### File Format Tips
- **Patient IDs must match exactly** (case-sensitive) across all files
- **Use Excel format** for files with special characters (Unicode, symbols)
- **CSV files** must use comma separator, TSV files must use tab separator
- **Remove extra columns** that don't contain patient data
- **Check for hidden spaces** in patient IDs or gene names

---

## 💡 Best Practices

1. **Start with small files** to verify your pipeline works
2. **Keep patient IDs consistent** across all your files
3. **Use Excel format** if you have special characters or accented text
4. **Set zero threshold to 100%** initially, then adjust if needed
5. **Check first few rows** of output to verify correctness

---

## 🔒 Privacy & Security

- **100% Offline:** All processing happens locally on your computer
- **No Internet Required:** Your data never leaves your machine
- **No Tracking:** The tool doesn't collect any usage statistics
- **Secure:** Your genomic data remains completely private

---

## 📞 Support

For issues not covered here:
1. Verify your files match the required structure exactly
2. Contact your IT administrator for system-specific issues

---

**Version 2.0** | Data Merger Tool | Enjoy merging your genomic data!"""

def build_executable():
    """Build the single executable file"""
    
    # Clean previous builds
    print("🧹 Cleaning previous builds...")
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"   Removed {folder}/")
    
    for file in os.listdir('.'):
        if file.endswith('.spec'):
            os.remove(file)
            print(f"   Removed {file}")
    
    # Build arguments for single file
    args = [
        'gui_launcher.py',
        '--onefile',
        '--windowed',
        '--name=Data_Merger_Tool',
        '--clean',
        '--noconfirm',
        
        # Add data files
        '--add-data=tcga_web_app/templates;templates',
        '--add-data=tcga_web_app/static;static',
        
        # Hidden imports for libraries that might not be detected
        '--hidden-import=polars',
        '--hidden-import=openpyxl',
        '--hidden-import=xlsxwriter',
        '--hidden-import=xlsx2csv',
        '--hidden-import=flask',
        '--hidden-import=waitress',
        '--hidden-import=pywebview',
        '--hidden-import=webview',
        
        # Collect all data for specific packages
        '--collect-all=polars',
        '--collect-all=flask',
        '--collect-all=openpyxl',
        
        # Optimization
        '--optimize=1',
    ]
    
    # Add icon if it exists
    if os.path.exists('tcga_icon.ico'):
        args.append('--icon=tcga_icon.ico')
        print("🎨 Using icon: tcga_icon.ico")
    
    print("\n🔨 Building single executable...")
    print("   This may take 2-5 minutes...")
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)
    
    # Check if build was successful
    exe_path = "dist/Data_Merger_Tool.exe"
    if os.path.exists(exe_path):
        exe_size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n✅ Build successful!")
        print(f"   Executable: {exe_path}")
        print(f"   Size: {exe_size:.1f} MB")
    else:
        print("\n❌ Build failed! Check error messages above.")
        return False
    
    return True

def create_distribution_package():
    """Create the distribution package with exe and README only"""
    
    print("\n📦 Creating distribution package...")
    
    # Check if exe exists
    if not os.path.exists("dist/Data_Merger_Tool.exe"):
        print("❌ Error: Build the exe first!")
        return False
    
    # Create package folder
    version = "2.0"  # Updated version
    package_name = f"Data_Merger_Tool_v{version}"
    
    if os.path.exists(package_name):
        shutil.rmtree(package_name)
    os.makedirs(package_name)
    print(f"   Created folder: {package_name}/")
    
    # Copy executable
    print("   Copying Data_Merger_Tool.exe...")
    shutil.copy("dist/Data_Merger_Tool.exe", package_name)
    
    # Create enhanced README
    print("   Creating README.txt...")
    readme_content = create_readme_content()
    with open(f"{package_name}/README.txt", "w", encoding='utf-8') as f:
        f.write(readme_content)
    
    # Create ZIP file with just exe and README
    print(f"\n📦 Creating ZIP file...")
    zip_name = f"{package_name}.zip"
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add only the exe and README
        zipf.write(f"{package_name}/Data_Merger_Tool.exe", "Data_Merger_Tool_v2.0/Data_Merger_Tool.exe")
        zipf.write(f"{package_name}/README.txt", "Data_Merger_Tool_v2.0/README.txt")
        print(f"   Added: Data_Merger_Tool.exe")
        print(f"   Added: README.txt")
    
    # Clean up temporary folder
    shutil.rmtree(package_name)
    
    # Get final statistics
    zip_size = os.path.getsize(zip_name) / (1024 * 1024)
    
    print("\n" + "="*60)
    print("✅ DISTRIBUTION PACKAGE CREATED SUCCESSFULLY!")
    print("="*60)
    print(f"📦 Package: {zip_name}")
    print(f"📏 Size: {zip_size:.1f} MB")
    print(f"📁 Structure:")
    print(f"   Data_Merger_Tool_v2.0.zip")
    print(f"   ├── Data_Merger_Tool.exe")
    print(f"   └── README.txt")
    print(f"\n🚀 Ready to distribute to researchers!")
    print(f"📧 Send the '{zip_name}' file")
    print("="*60)
    
    return True

def main():
    """Main build process"""
    print("\n" + "="*60)
    print("DATA MERGER TOOL - BUILD SCRIPT")
    print("="*60)
    
    # Step 1: Build executable
    if not build_executable():
        print("\n❌ Build failed. Please fix errors and try again.")
        return
    
    # Step 2: Create distribution package
    if not create_distribution_package():
        print("\n❌ Package creation failed.")
        return
    
    print("\n✨ All done! Your tool is ready for distribution.")

if __name__ == "__main__":
    main()