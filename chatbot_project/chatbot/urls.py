from django.urls import path
from .views import flujo_dptos_casas, chatbot_index
from django.views.generic import TemplateView

urlpatterns = [
    # otras urls...
    path('flujo_dptos_casas/', flujo_dptos_casas, name='flujo_dptos_casas'),
    path('chatbot_index/', chatbot_index, name='chatbot_index'),  
    path('test-chatbot/', TemplateView.as_view(template_name="test_chatbot.html")),
]