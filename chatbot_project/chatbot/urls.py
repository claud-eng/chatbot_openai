from django.urls import path
from .views import chat, chat_view
from django.views.generic import TemplateView

urlpatterns = [
    # otras urls...
    path('chat/', chat, name='chat'),
    path('chat-interface/', chat_view, name='chat_view'),  # Puedes cambiar 'chat-interface' a lo que prefieras.
    path('test-chatbot/', TemplateView.as_view(template_name="test_chatbot.html")),
]