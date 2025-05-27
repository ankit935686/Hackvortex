from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('air-quality/', views.air_quality, name='air_quality'),
    path('traffic/', views.traffic, name='traffic'),
    path('complaints/', views.complaints_view, name='complaints'),
    path('complaints/submit/', views.submit_complaint, name='submit_complaint'),
    path('complaints/list/', views.get_complaints, name='get_complaints'),
    path('logout/', LogoutView.as_view(next_page='landing'), name='logout'),
    
    # New notification and location routes
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('update-location/', views.update_location, name='update_location'),
    path('nearby-incidents/', views.nearby_incidents, name='nearby_incidents'),
    path('rain-alerts/', views.rain_alerts, name='rain_alerts'),
    path('traffic/report/', views.report_traffic_issue, name='report_traffic'),
    path('traffic/reports/', views.get_traffic_reports, name='get_traffic_reports'),
    path('traffic/report/<int:report_id>/verify/', views.verify_report, name='verify_report'),
    path('traffic/report/<int:report_id>/close/', views.close_report, name='close_report'),
    path('energy-usage/', views.energy_usage, name='energy_usage'),
    path('alerts/', views.alerts_view, name='alerts'),
]

