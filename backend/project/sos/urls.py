from django.urls import path
from . import views

app_name = 'sos'  # add namespace

urlpatterns = [
    path('emergency/', views.emergency_assistance, name='emergency'),
    path('emergency/submit/', views.submit_emergency, name='submit_emergency'),
]
