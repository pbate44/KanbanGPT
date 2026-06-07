
/**
 * Show a toast notification
 * @param {string} type - The type of toast ('success', 'error', 'warning', 'info')
 * @param {string} title - The title of the toast
 * @param {string} message - The message content
 * @param {number} delay - Auto-hide delay in milliseconds (default: 5000)
 */

function showToast(type, title, message, delay = 5000) {
  const toastContainer = document.querySelector('.toast-container');
  if (!toastContainer) {
    console.warn('Toast container not found');
    return;
  }

  const toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);

  const toastTypes = {
    success: {
      bgClass: 'bg-success',
      textClass: 'text-white',
      icon: 'bi-check-circle-fill'
    },
    error: {
      bgClass: 'bg-danger',
      textClass: 'text-white',
      icon: 'bi-exclamation-triangle-fill'
    },
    warning: {
      bgClass: 'bg-warning',
      textClass: 'text-dark',
      icon: 'bi-exclamation-triangle-fill'
    },
    info: {
      bgClass: 'bg-info',
      textClass: 'text-white',
      icon: 'bi-info-circle-fill'
    }
  };

  const toastConfig = toastTypes[type] || toastTypes.info;

  const toastHtml = `
    <div id="${toastId}" class="toast ${toastConfig.bgClass} ${toastConfig.textClass}" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="${delay}">
      <div class="toast-header ${toastConfig.bgClass} ${toastConfig.textClass} border-0">
        <i class="bi ${toastConfig.icon} me-2"></i>
        <strong class="me-auto">${escapeHtml(title)}</strong>
        <button type="button" class="btn-close ${toastConfig.textClass === 'text-white' ? 'btn-close-white' : ''}" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">
        ${escapeHtml(message)}
      </div>
    </div>
  `;

  toastContainer.insertAdjacentHTML('beforeend', toastHtml);

  const toastElement = document.getElementById(toastId);
  const toast = new bootstrap.Toast(toastElement);
  toast.show();

  toastElement.addEventListener('hidden.bs.toast', function() {
    toastElement.remove();
  });

  return toast;
}

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - The text to escape
 * @returns {string} - The escaped text
 */

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

/**
 * Show a success toast
 * @param {string} title - The title of the toast
 * @param {string} message - The message content
 */

function showSuccessToast(title, message) {
  return showToast('success', title, message);
}

/**
 * Show an error toast
 * @param {string} title - The title of the toast
 * @param {string} message - The message content
 */

function showErrorToast(title, message) {
  return showToast('error', title, message);
}

/**
 * Show a warning toast
 * @param {string} title - The title of the toast
 * @param {string} message - The message content
 */

function showWarningToast(title, message) {
  return showToast('warning', title, message);
}

/**
 * Show an info toast
 * @param {string} title - The title of the toast
 * @param {string} message - The message content
 */

function showInfoToast(title, message) {
  return showToast('info', title, message);
}
