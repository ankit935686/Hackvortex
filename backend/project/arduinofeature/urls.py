from django.urls import path
from . import views

app_name = 'arduinofeature'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('monitor/', views.smoke_monitor, name='smoke_monitor'),
    path('get-smoke-data/', views.get_smoke_data, name='get_smoke_data'),
    path('graphical-data/', views.graphical_data, name='graphical_data'),
    path('get-chart-data/', views.get_chart_data, name='get_chart_data'),
    path('ai-suggestion/', views.ai_suggestion, name='ai_suggestion'),
    path('get-ai-suggestions/', views.get_ai_suggestions, name='get_ai_suggestions'),
]
