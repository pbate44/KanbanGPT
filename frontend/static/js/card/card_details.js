
$(function () {

  $(document).on("click", "#cardTitleDisplay, #editCardTitleBtn", function () {
    var $cardTitle = $(this).attr("id") === "editCardTitleBtn"
      ? $("#cardTitleDisplay")
      : $(this);

    if ($cardTitle.find("input").length) return;

    var cardId = $cardTitle.data("card-id");
    var currentTitle = $cardTitle.text().trim();

    var $input = $('<input type="text" id="cardTitleInput" class="form-control">').val(currentTitle);
    $cardTitle.empty().append($input);

    $input.css({ "width": "100%"});

    $input.focus().select();

    $input.on("blur", function () {
      $(this).css("width", "100%");
      saveCardTitle();
    });

    $input.on("keypress", function (e) {
      if (e.which === 13) { e.preventDefault(); saveCardTitle(); }
    });

    function saveCardTitle() {
      var newTitle = $input.val().trim();
      if (newTitle && newTitle !== currentTitle) {
        $.ajax({
          url: "/update-card-description/" + cardId + "/",
          method: "POST",
          data: JSON.stringify({ title: newTitle }),
          contentType: "application/json",
          headers: { "X-CSRFToken": CSRF_TOKEN },
          success: function () {
            $cardTitle.text(newTitle);
            $("#cardDetailLabel").text(newTitle);
            $(".card-item[data-card-id='" + cardId + "'] .card-content")
              .text(newTitle).closest(".card-item").attr("data-card-title", newTitle);
          },
          error: function () {
            alert("Failed to update card title. Please try again.");
            $cardTitle.text(currentTitle);
          },
        });
      } else {
        $cardTitle.text(currentTitle);
      }
      $input.off("blur keypress");
    }
  });

  $("#editBoardTitleBtn").on("click", function () {
    var $boardTitle = $("#boardTitle");
    var currentTitle = $boardTitle.text().trim();

    var $input = $('<input type="text" id="boardTitleInput" class="form-control form-control-lg">').val(currentTitle);
    $boardTitle.empty().append($input);
    $input.focus().select();
    $input.on("blur", saveBoardTitle);
    $input.on("keypress", function (e) { if (e.which === 13) saveBoardTitle(); });

    function saveBoardTitle() {
      var newTitle = $input.val().trim();
      if (newTitle && newTitle !== currentTitle) {
        var boardId = window.location.pathname.match(/\/board\/(\d+)\//)[1];
        $.ajax({
          url: "/update-board-title/" + boardId + "/",
          method: "POST",
          data: JSON.stringify({ title: newTitle }),
          contentType: "application/json",
          headers: { "X-CSRFToken": CSRF_TOKEN },
          success: function () { $boardTitle.text(newTitle); },
          error: function () {
            alert("Failed to update board title. Please try again.");
            $boardTitle.text(currentTitle);
          },
        });
      } else {
        $boardTitle.text(currentTitle);
      }
      $input.off("blur keypress");
    }
  });

  $(document).on("click", ".deleteCardBtn, #dropdownDeleteCardBtn", function () {
    var cardId = $(this).data("card-id");
    var cardTitle = $(".card-title-text").text() || "Untitled Card";
    $("#cardToDelete .card-title-preview").text(cardTitle);
    $("#confirmDeleteCardBtn").data("card-id", cardId);
    showModal(document.getElementById("deleteCardModal"));
  });

  $(document).on("click", "#confirmDeleteCardBtn", function () {
    var cardId = $(this).data("card-id");

    $.ajax({
      url: "/delete-card/" + cardId + "/",
      method: "POST",
      headers: { "X-CSRFToken": CSRF_TOKEN },
      success: function () {
        $(".card-item[data-card-id='" + cardId + "']").remove();
        hideModal(document.getElementById("deleteCardModal"));
        hideModal(document.getElementById("cardDetailModal"));
      },
      error: function (xhr) {
        console.error("Error deleting card:", xhr.responseText);
      },
    });
  });

  $(document).on("click", '.cancelDeleteCardBtn, [data-bs-dismiss="modal"]', function () {
    $("#deleteCardModal").modal("hide");
    $("#confirmDeleteCardBtn").removeData("card-id");
  });

  function updateButtonStates() {
    var swimlaneCount = document.querySelectorAll(".swimlane-row").length;
    var columnCount = document.querySelectorAll(".column-header").length;

    var $swimlaneBtn = $("#addSwimlaneBtn");
    if (swimlaneCount >= 7) {
      $swimlaneBtn.prop("disabled", true).removeClass("btn-outline-primary")
        .addClass("btn-outline-secondary").attr("title", "Maximum swimlanes reached (7/7)");
    } else {
      $swimlaneBtn.prop("disabled", false).removeClass("btn-outline-secondary")
        .addClass("btn-outline-primary").attr("title", "Add new swimlane (" + swimlaneCount + "/7)");
    }
    var swimlaneCountEl = document.getElementById("swimlaneCurrentCount");
    if (swimlaneCountEl) swimlaneCountEl.textContent = swimlaneCount;

    var $columnBtn = $("#addColumnBtn");
    if (columnCount >= 7) {
      $columnBtn.prop("disabled", true).removeClass("btn-outline-primary")
        .addClass("btn-outline-secondary").attr("title", "Maximum columns reached (7/7)");
    } else {
      $columnBtn.prop("disabled", false).removeClass("btn-outline-secondary")
        .addClass("btn-outline-primary").attr("title", "Add new column (" + columnCount + "/7)");
    }
  }

  window.updateButtonStates = updateButtonStates;

  updateButtonStates();

  var observer = new MutationObserver(updateButtonStates);
  observer.observe(document.querySelector(".kanban-board"), { childList: true, subtree: true });

  function initializePostButton() {
    var postButton = document.querySelector(".post-entry-btn");
    var textarea = document.getElementById("logEntryTextarea");
    var form = document.getElementById("logEntryForm");

    if (postButton && textarea && form) {
      function togglePostButton() {
        postButton.disabled = textarea.value.trim().length === 0;
      }
      textarea.addEventListener("input", togglePostButton);
      togglePostButton();

      form.addEventListener("submit", function (e) {
        if (textarea.value.trim().length === 0) { e.preventDefault(); return; }
        postButton.disabled = true;
        postButton.innerHTML = '<i class="bi bi-hourglass-split"></i>';
      });

      textarea.addEventListener("keydown", function (e) {
        if ((e.ctrlKey || e.shiftKey) && e.key === "Enter") {
          e.preventDefault();
          if (textarea.value.trim().length > 0) form.dispatchEvent(new Event("submit"));
        }
      });
    }
  }

  function initializeAttachmentsToggle() {
    var attachmentsToggleBtn = document.querySelector(".attachments-toggle-btn");
    var attachmentsContent = document.getElementById("attachmentsContent");
    var cardId = document.querySelector(".card-detail-container")?.dataset.cardId;

    if (!attachmentsToggleBtn || !attachmentsContent || !cardId) return;

    var storageKey = "attachments-expanded-" + cardId;
    var savedState = localStorage.getItem(storageKey);
    var isExpanded = savedState !== null ? savedState === "true" : false;

    if (isExpanded) {
      attachmentsContent.classList.add("show");
      attachmentsToggleBtn.setAttribute("aria-expanded", "true");
      attachmentsToggleBtn.querySelector("i").className = "attachment-toggle bi bi-chevron-down";
    } else {
      attachmentsContent.classList.remove("show");
      attachmentsToggleBtn.setAttribute("aria-expanded", "false");
      attachmentsToggleBtn.querySelector("i").className = "attachment-toggle bi bi-chevron-right";
    }

    attachmentsContent.addEventListener("show.bs.collapse", function () {
      attachmentsToggleBtn.querySelector("i").className = "attachment-toggle bi bi-chevron-down";
      attachmentsToggleBtn.setAttribute("aria-expanded", "true");
    });
    attachmentsContent.addEventListener("shown.bs.collapse", function () {
      localStorage.setItem(storageKey, "true");
    });
    attachmentsContent.addEventListener("hide.bs.collapse", function () {
      attachmentsToggleBtn.querySelector("i").className = "attachment-toggle bi bi-chevron-right";
      attachmentsToggleBtn.setAttribute("aria-expanded", "false");
    });
    attachmentsContent.addEventListener("hidden.bs.collapse", function () {
      localStorage.setItem(storageKey, "false");
    });
  }

  function initializeSubtasks() {
    var subtasksToggleBtn = document.querySelector(".subtasks-toggle-btn");
    var subtasksContent = document.getElementById("subtasksContent");
    var cardId = document.querySelector(".card-detail-container")?.dataset.cardId;

    if (!subtasksToggleBtn || !subtasksContent || !cardId) return;

    var storageKey = "subtasks-expanded-" + cardId;
    var savedState = localStorage.getItem(storageKey);
    var isExpanded = savedState !== null ? savedState === "true" : false;

    if (isExpanded) {
      subtasksContent.classList.add("show");
      subtasksToggleBtn.setAttribute("aria-expanded", "true");
      subtasksToggleBtn.querySelector("i").className = "bi bi-chevron-down";
    } else {
      subtasksContent.classList.remove("show");
      subtasksToggleBtn.setAttribute("aria-expanded", "false");
      subtasksToggleBtn.querySelector("i").className = "bi bi-chevron-right";
    }

    subtasksContent.addEventListener("show.bs.collapse", function () {
      subtasksToggleBtn.querySelector("i").className = "bi bi-chevron-down";
      subtasksToggleBtn.setAttribute("aria-expanded", "true");
    });
    subtasksContent.addEventListener("shown.bs.collapse", function () {
      localStorage.setItem(storageKey, "true");
      loadSubtasks(cardId);
    });
    subtasksContent.addEventListener("hide.bs.collapse", function () {
      subtasksToggleBtn.querySelector("i").className = "bi bi-chevron-right";
      subtasksToggleBtn.setAttribute("aria-expanded", "false");
    });
    subtasksContent.addEventListener("hidden.bs.collapse", function () {
      localStorage.setItem(storageKey, "false");
    });

    initializeSubtaskForm(cardId);
    if (cardId) loadSubtasks(cardId);
  }

  function initializeSubtaskForm(cardId) {
    var addSubtaskBtn = document.getElementById("addSubtaskBtn");
    var newSubtaskInput = document.getElementById("newSubtaskInput");
    var saveSubtaskBtn = document.getElementById("saveSubtaskBtn");
    var cancelSubtaskBtn = document.getElementById("cancelSubtaskBtn");
    var subtasksContent = document.getElementById("subtasksContent");
    var subtasksToggleBtn = document.querySelector(".subtasks-toggle-btn");

    if (addSubtaskBtn) {
      addSubtaskBtn.addEventListener("click", function (e) {
        e.preventDefault();
        if (!subtasksContent.classList.contains("show")) {
          subtasksToggleBtn.click();
          setTimeout(showSubtaskForm, 300);
        } else {
          showSubtaskForm();
        }
      });
    }

    if (saveSubtaskBtn) {
      saveSubtaskBtn.addEventListener("click", function (e) {
        e.preventDefault();
        var name = newSubtaskInput.value.trim();
        if (name) saveSubtask(cardId, name);
      });
    }

    if (cancelSubtaskBtn) {
      cancelSubtaskBtn.addEventListener("click", function (e) {
        e.preventDefault();
        hideSubtaskForm();
      });
    }

    if (newSubtaskInput) {
      newSubtaskInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          var name = this.value.trim();
          if (name) saveSubtask(cardId, name);
        } else if (e.key === "Escape") {
          e.preventDefault();
          hideSubtaskForm();
        }
      });
    }
  }

  function initializeEventDelegation() {
    document.addEventListener("click", function (e) {
      var copyBtn = e.target.closest("#copyEmailBtn");
      if (copyBtn) {
        e.preventDefault();
        e.stopPropagation();
        copyEmailToClipboard(copyBtn.dataset.email);
        return;
      }

      if (e.target && e.target.id === "addSubtaskBtn") {
        e.preventDefault();
        var cardId = document.querySelector(".card-detail-container")?.dataset.cardId;
        var subtasksContent = document.getElementById("subtasksContent");
        var subtasksToggleBtn = document.querySelector(".subtasks-toggle-btn");
        if (cardId) {
          if (!subtasksContent.classList.contains("show")) {
            subtasksToggleBtn.click();
            setTimeout(showSubtaskForm, 300);
          } else {
            showSubtaskForm();
          }
        }
      }

      if (e.target && e.target.id === "saveSubtaskBtn") {
        e.preventDefault();
        var cardId = document.querySelector(".card-detail-container")?.dataset.cardId;
        var input = document.getElementById("newSubtaskInput");
        var name = input?.value.trim();
        if (name && cardId) saveSubtask(cardId, name);
      }

      if (e.target && e.target.id === "cancelSubtaskBtn") {
        e.preventDefault();
        hideSubtaskForm();
      }
    });
  }

  function initializeCardModal() {
    initializePostButton();
    initializeAttachmentsToggle();
    initializeSubtasks();
    initializeEventDelegation();
  }

  window.initializeCardModal = initializeCardModal;
  window.showSubtaskForm = showSubtaskForm;
  window.hideSubtaskForm = hideSubtaskForm;
  window.loadSubtasks = loadSubtasks;
  window.saveSubtask = saveSubtask;
  window.toggleSubtask = toggleSubtask;
  window.deleteSubtask = deleteSubtask;
  window.renderSubtasks = renderSubtasks;
  window.updateSubtasksCount = updateSubtasksCount;
  window.copyEmailToClipboard = copyEmailToClipboard;
  window.getContrastColor = getContrastColor;

  document.addEventListener("DOMContentLoaded", initializeCardModal);

  document.addEventListener("shown.bs.modal", function (event) {
    if (event.target && event.target.id === "cardDetailModal") {
      setTimeout(initializeCardModal, 100);
    }
  });

});
