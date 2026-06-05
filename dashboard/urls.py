from django.urls import path
from . import views

urlpatterns = [
    path('',                         views.home,        name='home'),
    path('task/<int:task_id>/toggle/', views.toggle_task, name='toggle_task'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
]