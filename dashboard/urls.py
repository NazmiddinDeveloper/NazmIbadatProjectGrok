from django.urls import path
from . import views

urlpatterns = [
    path('',                         views.home,        name='home'),
    path('smenalar/', views.smenalar, name='smenalar'),
    path('task/<int:task_id>/toggle/', views.toggle_task, name='toggle_task'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('api/quests/', views.get_daily_quests_api, name='get_daily_quests_api'),
]

