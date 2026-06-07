from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from frontend.views.ai import card_ai_chat, card_ai_history, clear_chat_history, list_chat_sessions, new_chat_session, delete_chat_session
from frontend.views.attachments import delete_attachment, get_attachments, upload_attachment, view_attachment
from frontend.views.auth import Login, Signup, delete_account, goodbye, logout_view, verify_2fa
from frontend.views.board import (
    board_data_api,
    board_detail,
    create_board,
    delete_board,
    get_board_details,
    remove_board_image,
    update_board,
    update_board_title,
    upload_board_image,
)
from frontend.views.card import (
    add_card,
    card_detail,
    delete_card,
    delete_log_entry,
    export_card_log_pdf,
    move_card_api,
    update_card_color,
    update_card_description,
    update_card_position,
    update_card_priority,
    update_card_swimlane,
    update_log_entry,
)
from frontend.views.column import (
    add_column,
    delete_column,
    save_column_sort_order,
    update_card_position_manual,
    update_column_name,
)
from frontend.views.dashboard import dashboard
from frontend.views.pages import about_us, contact_us, contact_us_success, docs, home, privacy_policy, terms_of_service
from frontend.views.settings import (
    edit_email,
    edit_password,
    edit_theme,
    edit_username,
    get_openrouter_models,
    save_ai_model,
    user_settings,
)
from frontend.views.subtasks import add_subtask, delete_subtask, list_subtasks, toggle_subtask, update_subtask
from frontend.views.swimlane import add_swimlane, delete_swimlane, update_swimlane_name

urlpatterns = [

    path('',                    home,               name='home'),
    path('login/',              Login,              name='login'),
    path('verify-2fa/',         verify_2fa,         name='verify_2fa'),
    path('sign-up/',            Signup,             name='signup'),
    path('logout/',             logout_view,        name='logout'),
    path('contact-us/',         contact_us,         name='contact_us'),
    path('contact-us/success/', contact_us_success, name='contact_us_success'),
    path('about-us/',           RedirectView.as_view(url='/#story', permanent=True), name='about_us'),
    path('privacy-policy/',     privacy_policy,     name='privacy_policy'),
    path('terms-of-service/',   terms_of_service,   name='terms_of_service'),
    path('docs/',               docs,               name='docs'),

    path(
        "forgot-password/",
        auth_views.PasswordResetView.as_view(
            template_name="forgot_password.html",
            email_template_name="emails/password_reset_email.txt",
            subject_template_name="emails/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "forgot-password/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="forgot_password_sent.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    path("settings/delete-account/", delete_account, name="delete_account"),
    path("goodbye/",                 goodbye,        name="goodbye"),

    path('board/<int:board_id>/',            board_detail,      name='board_detail'),
    path('cards/<int:card_id>/',             card_detail,       name='card_detail'),
    path('cards/<int:card_id>/export_pdf/',  export_card_log_pdf, name='export_card_log_pdf'),
    path('update-card-position/',            update_card_position, name='update_card_position'),
    path('add-card/',                        add_card,          name='add_card'),
    path('update-board-title/<int:board_id>/', update_board_title, name='update_board_title'),
    path('add-column/',                      add_column,        name='add_column'),
    path('update-column-name/<int:column_id>/', update_column_name, name='update_column_name'),
    path('delete-column/<int:column_id>/',   delete_column,     name='delete_column'),
    path('add-swimlane/',                    add_swimlane,      name='add_swimlane'),
    path('update-swimlane-name/<int:swimlane_id>/', update_swimlane_name, name='update_swimlane_name'),
    path('delete-swimlane/<int:swimlane_id>/', delete_swimlane, name='delete_swimlane'),
    path('update-card-swimlane/',            update_card_swimlane, name='update_card_swimlane'),
    path('api/board/<int:board_id>/data/',   board_data_api,    name='board_data_api'),
    path('move-card/<int:card_id>/',         move_card_api,     name='move_card_api'),
    path('save-column-sort-order/',          save_column_sort_order, name='save_column_sort_order'),
    path('update-card-position-manual/',     update_card_position_manual, name='update_card_position_manual'),

    path('cards/<int:card_id>/add-log-entry/',           card_detail,             name='add_log_entry'),
    path('delete-card/<int:card_id>/',                   delete_card,             name='delete_card'),
    path('update-card-description/<int:card_id>/',       update_card_description, name='update_card_description'),
    path('update-card-priority/<int:card_id>/',          update_card_priority,    name='update_card_priority'),
    path('update-card-color/<int:card_id>/',             update_card_color,       name='update_card_color'),
    path('delete-log-entry/<int:entry_id>/',             delete_log_entry,        name='delete_log_entry'),
    path('update-log-entry/<int:entry_id>/',             update_log_entry,        name='update_log_entry'),
    path('cards/<int:card_id>/attachments/upload/',      upload_attachment,       name='upload_attachment'),
    path('cards/<int:card_id>/attachments/',             get_attachments,         name='get_attachments'),
    path('attachments/<int:attachment_id>/view/',        view_attachment,         name='view_attachment'),
    path('attachments/<int:attachment_id>/delete/',      delete_attachment,       name='delete_attachment'),

    path('card/<int:card_id>/ai-chat/',                                      card_ai_chat,        name='card_ai_chat'),
    path('card/<int:card_id>/ai-chat/history/',                              card_ai_history,     name='card_ai_chat_history'),
    path('card/<int:card_id>/ai-chat/clear/',                                clear_chat_history,  name='clear_chat_history'),
    path('card/<int:card_id>/ai-chat/sessions/',                             list_chat_sessions,  name='list_chat_sessions'),
    path('card/<int:card_id>/ai-chat/sessions/new/',                         new_chat_session,    name='new_chat_session'),
    path('card/<int:card_id>/ai-chat/sessions/<int:session_id>/delete/',     delete_chat_session, name='delete_chat_session'),

    path('cards/<int:card_id>/subtasks/',       list_subtasks,   name='list_subtasks'),
    path('cards/<int:card_id>/subtasks/add/',   add_subtask,     name='add_subtask'),
    path('subtasks/<int:subtask_id>/toggle/',   toggle_subtask,  name='toggle_subtask'),
    path('subtasks/<int:subtask_id>/update/',   update_subtask,  name='update_subtask'),
    path('subtasks/<int:subtask_id>/delete/',   delete_subtask,  name='delete_subtask'),

    path('dashboard/',                          dashboard,         name='dashboard'),
    path('boards/create/',                      create_board,      name='create_board'),
    path('boards/<int:board_id>/update/',       update_board,      name='update_board'),
    path('boards/<int:board_id>/delete/',       delete_board,      name='delete_board'),
    path('boards/<int:board_id>/upload-image/', upload_board_image, name='upload_board_image'),
    path('boards/<int:board_id>/remove-image/', remove_board_image, name='remove_board_image'),
    path('boards/<int:board_id>/details/',      get_board_details,  name='get_board_details'),

    path('user_settings/',                  user_settings,      name='user_settings'),
    path('user_settings/edit_username/',    edit_username,      name='edit_username'),
    path('user_settings/edit_email/',       edit_email,         name='edit_email'),
    path('user_settings/edit_password/',    edit_password,      name='edit_password'),
    path('user_settings/edit_theme/',       edit_theme,         name='edit_theme'),
    path('settings/ai/model/save/',          save_ai_model,          name='save_ai_model'),
    path('settings/ai/models/',             get_openrouter_models,  name='get_openrouter_models'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
