from django.urls import path
from . import views

app_name = 'manager'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('smoke-monitor/', views.smoke_monitor_redirect, name='smoke_monitor_redirect'),
    path('complaints/', views.complaints_view, name='complaints'),
    path('complaints/update-status/', views.update_complaint_status, name='update_complaint_status'),
    path('complaints/filter/', views.filter_complaints, name='filter_complaints'),
    path('complaints/export-pdf/', views.export_complaints_pdf, name='export_complaints_pdf'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/send/', views.send_notification, name='send_notification'),
]
