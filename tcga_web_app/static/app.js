/**
 * TCGA Data Merger Tool - JavaScript Controller
 * 
 * This script manages all client-side functionality for the TCGA Data Merger web interface,
 * providing an interactive and user-friendly experience for genomic data processing.
 * 
 * Core Functionality:
 * - File upload handling with drag-and-drop support
 * - Real-time file validation and size checking
 * - Dynamic phenotype column preview via AJAX
 * - Form validation before submission
 * - Loading overlay with progress animation
 * - Toast notifications for user feedback
 * - Success modal management
 * 
 * Key Features:
 * - Drag & Drop: Full drag-and-drop file upload with visual feedback
 * - File Validation: Ensures correct file combinations (methylation+mapping, etc.)
 * - Size Management: Automatically disables Excel format for files >50MB
 * - Dynamic UI: Updates interface based on user selections
 * - Native Folder Picker: Integrates with PyWebView for desktop app
 * - Progress Tracking: Animated progress bar during processing
 * - Error Handling: Comprehensive validation with clear error messages
 * 
 * File Combination Rules:
 * - Methylation files MUST be paired with Gene Mapping files
 * - Gene Expression can be standalone or combined with others
 * - Phenotype files require either Expression or Methylation+Mapping
 * 
 * Technical Details:
 * - Uses Bootstrap 5 for modals and toasts
 * - Vanilla JavaScript (no jQuery dependency)
 * - AJAX communication with Flask backend
 * - DataTransfer API for drag-and-drop file handling
 * - FormData API for file uploads
 * 
 * Global Variables:
 * - totalFileSize: Tracks combined size of all uploaded files
 * - SIZE_LIMIT_MB: Maximum file size (50MB) before forcing CSV output
 */

// Global variables
let totalFileSize = 0;
const SIZE_LIMIT_MB = 50;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  initializeUI();
  initializeFileUploads();
  initializeSlider();
  initializeDragAndDrop();
  initializeModals();
});

// Initialize UI components
function initializeUI() {
  // Add smooth scroll behavior
  document.documentElement.style.scrollBehavior = 'smooth';
}

// Initialize file upload handlers
function initializeFileUploads() {
  const fileTypes = ['methylation', 'mapping', 'expression', 'phenotype'];
  
  fileTypes.forEach(type => {
    const dropZone = document.getElementById(`${type}-drop`);
    const fileInput = document.getElementById(`${type}-file`);
    const fileName = document.getElementById(`${type}-name`);
    
    if (!dropZone || !fileInput) return;
    
    // Click to upload
    dropZone.addEventListener('click', () => {
      fileInput.click();
    });
    
    // File input change
    fileInput.addEventListener('change', (e) => {
      handleFileSelect(e.target.files[0], type);
    });
  });
  
  // Special handling for phenotype file
  const phenotypeInput = document.getElementById('phenotype-file');
  if (phenotypeInput) {
    phenotypeInput.addEventListener('change', handlePhenotypeFile);
  }
}

// Handle file selection
function handleFileSelect(file, type) {
  if (!file) return;
  
  const dropZone = document.getElementById(`${type}-drop`);
  const fileName = document.getElementById(`${type}-name`);
  
  // Update UI
  dropZone.classList.add('has-file');
  fileName.textContent = file.name;
  fileName.style.color = 'var(--success)';
  
  // Check file size
  checkFileSizes();
  
  // Show success animation
  animateSuccess(dropZone);
}

// Animate success on file upload
function animateSuccess(element) {
  element.style.transform = 'scale(0.95)';
  setTimeout(() => {
    element.style.transform = 'scale(1)';
  }, 200);
}

// Initialize drag and drop
function initializeDragAndDrop() {
  const fileTypes = ['methylation', 'mapping', 'expression', 'phenotype'];
  
  fileTypes.forEach(type => {
    const dropZone = document.getElementById(`${type}-drop`);
    if (!dropZone) return;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, preventDefaults, false);
      document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, () => {
        dropZone.classList.add('drag-hover');
      }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, () => {
        dropZone.classList.remove('drag-hover');
      }, false);
    });
    
    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        const fileInput = document.getElementById(`${type}-file`);
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(files[0]);
        fileInput.files = dataTransfer.files;
        handleFileSelect(files[0], type);

        // Trigger change event for phenotype files
        if(type === 'phenotype') {
          fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
      }
    }, false);
  });
}

// Prevent default drag behaviors
function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

// Handle phenotype file selection
function handlePhenotypeFile(event) {
  const file = event.target.files[0];
  if (!file) {
    document.getElementById('phenotypeSelectWrapper').style.display = 'none';
    return;
  }
  
  const formData = new FormData();
  formData.append('phenotype_file', file);
  
  fetch('/preview_phenotype', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    const selectWrapper = document.getElementById('phenotypeSelectWrapper');
    const select = document.getElementById('phenotypeSelect');
    
    if (data.error) {
      showToast('error', 'Error reading phenotype file: ' + data.error);
      selectWrapper.style.display = 'none';
      return;
    }
    
    if (data.columns && data.columns.length > 0) {
      select.innerHTML = '';
      data.columns.forEach(col => {
        const option = document.createElement('option');
        option.value = col;
        option.textContent = col;
        select.appendChild(option);
      });
      selectWrapper.style.display = 'block';
    }
  })
  .catch(err => {
    showToast('error', 'Could not load phenotype characteristics.');
    console.error(err);
  });
}

// Initialize slider
function initializeSlider() {
  const slider = document.getElementById('zeroSlider');
  const valueDisplay = document.getElementById('zeroValue');
  const hiddenInput = document.getElementById('zeroInput');
  
  if (slider && valueDisplay && hiddenInput) {
    slider.addEventListener('input', function() {
      // Update display
      valueDisplay.textContent = this.value;
      // Update the hidden input that gets submitted
      hiddenInput.value = this.value;
      // Update slider fill visual
      const percent = (this.value / 100) * 100;
      this.style.background = `linear-gradient(to right, var(--primary) ${percent}%, var(--gray-200) ${percent}%)`;
    });
    
    // Initialize slider fill and value
    slider.dispatchEvent(new Event('input'));
  }
}

// Check file sizes and update format options
function checkFileSizes() {
  totalFileSize = 0;
  const fileInputs = document.querySelectorAll('input[type="file"]');
  
  fileInputs.forEach(input => {
    if (input.files && input.files[0]) {
      totalFileSize += input.files[0].size;
    }
  });
  
  const totalSizeMB = totalFileSize / (1024 * 1024);
  const excelOption = document.querySelector('input[value="excel"]').closest('.format-option');
  
  if (totalSizeMB > SIZE_LIMIT_MB) {
    excelOption.style.opacity = '0.5';
    excelOption.style.pointerEvents = 'none';
    document.querySelector('input[value="csv"]').checked = true;
    
    // Update format tip
    const formatTip = document.querySelector('.format-tip');
    formatTip.innerHTML = `
      <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"></path>
      </svg>
      Files larger than ${SIZE_LIMIT_MB}MB detected. Using CSV format for performance.
    `;
    formatTip.style.background = 'var(--warning-bg)';
    formatTip.style.color = 'var(--warning)';
  } else {
    excelOption.style.opacity = '1';
    excelOption.style.pointerEvents = 'auto';
  }
}

// Show loading with modern UI
function showLoading() {
  // Validate first
  if (!validateFileCombinations()) {
    return false;
  }
  
  // Check save folder
  const saveFolder = document.getElementById('saveFolder').value;
  if (!saveFolder) {
    showToast('error', 'Please choose a destination folder to save output files.');
    return false;
  }
  
  // Show loading overlay
  const overlay = document.getElementById('loadingOverlay');
  const progressBar = document.getElementById('progressBar');
  overlay.style.display = 'flex';
  
  // Disable submit button
  const runButton = document.getElementById('runButton');
  runButton.disabled = true;
  runButton.innerHTML = `
    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
    </svg>
    Processing...
  `;
  
  // Animate progress bar
  let progress = 2;
  progressBar.style.width = progress + '%';
  
  const progressInterval = setInterval(() => {
    progress += Math.random() * 15;
    if (progress > 90) {
      progress = 90;
      clearInterval(progressInterval);
    }
    progressBar.style.width = progress + '%';
  }, 500);
  
  return true;
}

// Validate file combinations
function validateFileCombinations() {
  const hasFiles = {
    methylation: document.getElementById('methylation-file').files.length > 0,
    mapping: document.getElementById('mapping-file').files.length > 0,
    expression: document.getElementById('expression-file').files.length > 0,
    phenotype: document.getElementById('phenotype-file').files.length > 0
  };
  
  // Check if at least one file is selected
  if (!hasFiles.methylation && !hasFiles.mapping && !hasFiles.expression && !hasFiles.phenotype) {
    showToast('error', 'Please upload at least one input file.');
    return false;
  }
  
  // Validate combinations
  const isValid = 
    (hasFiles.methylation && hasFiles.mapping && !hasFiles.expression && !hasFiles.phenotype) ||
    (hasFiles.methylation && hasFiles.mapping && hasFiles.expression && !hasFiles.phenotype) ||
    (hasFiles.methylation && hasFiles.mapping && hasFiles.expression && hasFiles.phenotype) ||
    (hasFiles.methylation && hasFiles.mapping && !hasFiles.expression && hasFiles.phenotype) ||
    (!hasFiles.methylation && !hasFiles.mapping && hasFiles.expression && !hasFiles.phenotype) ||
    (!hasFiles.methylation && !hasFiles.mapping && hasFiles.expression && hasFiles.phenotype);
  
  if (!isValid) {
    let errorMsg = '';
    if (hasFiles.methylation && !hasFiles.mapping) {
      errorMsg = 'A methylation file must be uploaded together with a gene mapping file.';
    } else if (hasFiles.mapping && !hasFiles.methylation) {
      errorMsg = 'A gene mapping file must be uploaded together with a methylation file.';
    } else if (hasFiles.phenotype && !hasFiles.methylation && !hasFiles.expression) {
      errorMsg = 'A phenotype file must be uploaded together with a gene expression file or methylation + mapping files.';
    } else {
      errorMsg = 'Invalid file combination. Please check the required file combinations.';
    }
    showToast('error', errorMsg);
    return false;
  }
  
  return true;
}

// Folder picker function
function pickFolder() {
  if (window.pywebview) {
    window.pywebview.api.select_folder().then(function(result) {
      if (result && result.length > 0) {
        document.getElementById('saveFolder').value = result[0];
      }
    });
  } else {
    // For web version, use a simple prompt
    const folder = prompt('Please enter the output folder path:');
    if (folder) {
      document.getElementById('saveFolder').value = folder;
    }
  }
}

// Show toast notifications
function showToast(type, message) {
  const toastContainer = document.getElementById('toastContainer') || createToastContainer();
  
  const toastHtml = `
    <div class="toast show" role="alert" data-bs-autohide="true" data-bs-delay="5000">
      <div class="toast-header bg-${type === 'error' ? 'danger' : type} text-white">
        <strong class="me-auto">${type === 'error' ? '❌ Error' : '✅ Success'}</strong>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
      </div>
      <div class="toast-body">
        ${message}
      </div>
    </div>
  `;
  
  const toastElement = document.createElement('div');
  toastElement.innerHTML = toastHtml;
  toastContainer.appendChild(toastElement.firstElementChild);
  
  const toast = new bootstrap.Toast(toastContainer.lastElementChild);
  toast.show();
}

// Create toast container
function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toastContainer';
  container.className = 'toast-container position-fixed top-0 end-0 p-3';
  container.style.zIndex = '1050';
  container.style.marginTop = '80px';
  document.body.appendChild(container);
  return container;
}

// Initialize modals
function initializeModals() {
  // Auto-show success modal if present
  const successModal = document.getElementById('successModal');
  if (successModal) {
    const modal = new bootstrap.Modal(successModal);
    modal.show();
  }
  
  // Initialize existing toasts
  const toastElList = document.querySelectorAll('.toast');
  const toastList = [...toastElList].map(toastEl => new bootstrap.Toast(toastEl));
  toastList.forEach(toast => toast.show());
}
