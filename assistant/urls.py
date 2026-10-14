from django.urls import path

from . import views

urlpatterns = [
    path('member/assistant/', views.chat_home, name='assistant-chat'),
    path('member/assistant/new/', views.new_session, name='assistant-new-session'),
    path('member/assistant/<int:session_id>/delete/', views.delete_session, name='assistant-delete-session'),
    path('member/assistant/send/', views.send_message, name='assistant-send'),
    path('member/assistant/action/<int:pending_action_id>/resolve/', views.resolve_action, name='assistant-resolve-action'),
    path('member/assistant/language/', views.set_language, name='assistant-set-language'),
]
