from django.urls import path
from .views import chat, chat_view

urlpatterns = [
    # otras urls...
    path('chat/', chat, name='chat'),
    path('chat-interface/', chat_view, name='chat_view'),  # Puedes cambiar 'chat-interface' a lo que prefieras.
]