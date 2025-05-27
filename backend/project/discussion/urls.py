from django.urls import path
from . import views

urlpatterns = [
    path('', views.discussions_view, name='discussions'),
    path('create/', views.create_discussion, name='create_discussion'),
    path('<int:discussion_id>/comment/', views.add_comment, name='add_comment'),
] 