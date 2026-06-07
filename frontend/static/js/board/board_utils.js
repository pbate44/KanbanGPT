
var CSRF_TOKEN = (function () {
  var el = document.querySelector("[name=csrfmiddlewaretoken]");
  if (el) return el.value;
  return getCookie("csrftoken") || "";
})();

function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i++) {
      var cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function showModal(el) {
  if (!el) return;
  bootstrap.Modal.getOrCreateInstance(el).show();
}

function hideModal(el) {
  if (!el) return;
  var instance = bootstrap.Modal.getInstance(el);
  if (instance) instance.hide();
}

function escapeHtml(str) {
  var d = document.createElement("div");
  d.textContent = str ?? "";
  return d.innerHTML;
}

function showSuccessToast(title, message) {
  _showToastNotification(title, message, "bg-success", "bi-check-circle");
}

function showErrorToast(title, message) {
  _showToastNotification(title, message, "bg-danger", "bi-exclamation-circle");
}

function _showToastNotification(title, message, bgClass, iconClass) {
  var $notification = $(
    '<div class="position-fixed top-0 end-0 p-3" style="z-index: 1080"></div>'
  );
  var $body = $('<div class="toast-body"></div>').append(
    $('<i>').addClass('bi ' + iconClass + ' me-2'),
    $('<strong></strong>').text(title),
    document.createTextNode(' ' + message)
  );
  var $toast = $('<div class="toast align-items-center text-white ' + bgClass + ' border-0" role="alert" aria-live="assertive" aria-atomic="true">' +
    '<div class="d-flex">' +
    '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
    '</div></div>');
  $toast.find('.d-flex').prepend($body);
  $notification.append($toast);
  $("body").append($notification);
  var toast = new bootstrap.Toast($toast[0], { delay: 3000, autohide: true });
  toast.show();
  $toast.on("hidden.bs.toast", function () { $notification.remove(); });
}