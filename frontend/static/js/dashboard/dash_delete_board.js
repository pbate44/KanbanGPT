
import { getCookie, setButtonLoading } from './dash_utils.js';
import { removeBoardFromGrid } from './dash_grid.js';

export function openDeleteBoardModal(boardId, boardName) {
    $('#deleteBoardId').val(boardId);
    $('#deleteBoardName').text(boardName);
    $('#confirmBoardName').text(boardName);
    $('#deleteConfirmInput').val('');
    $('#confirmDeleteBoard').prop('disabled', true);
    
    $('#deleteBoardModal').modal('show');
}

export function validateDeleteConfirmation() {
    const expectedName = $('#confirmBoardName').text();
    const enteredName = $('#deleteConfirmInput').val();
    const isValid = enteredName === expectedName;
    
    $('#confirmDeleteBoard').prop('disabled', !isValid);
    
    if (enteredName.length > 0 && !isValid) {
        $('#deleteConfirmInput').addClass('is-invalid');
    } else {
        $('#deleteConfirmInput').removeClass('is-invalid');
    }
}

export function handleDeleteBoard() {
    const $btn = $('#confirmDeleteBoard');
    const boardId = $('#deleteBoardId').val();
    
    setButtonLoading($btn, true);
    
    $.ajax({
        url: `/boards/${boardId}/delete/`,
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        success: function(data) {
            $('#deleteBoardModal').modal('hide');
            removeBoardFromGrid(boardId);
        },
        error: function(xhr) {
            let errorData = { error: 'An error occurred' };
            try {
                errorData = JSON.parse(xhr.responseText);
            } catch (e) {
                errorData = { error: xhr.statusText || 'Failed to delete board' };
            }
        },
        complete: function() {
            setButtonLoading($btn, false);
        }
    });
}