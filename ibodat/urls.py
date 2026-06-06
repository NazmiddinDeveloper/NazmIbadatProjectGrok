from django.urls import path
from . import views

urlpatterns = [
    path('',                         views.ibodat,        name='ibodat'),
    path('toggle/<str:prayer_key>/', views.toggle_prayer, name='toggle_prayer'),
    path('tarix/',                   views.history,       name='prayer_history'),
]