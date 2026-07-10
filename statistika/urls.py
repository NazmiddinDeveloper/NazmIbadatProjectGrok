from django.urls import path
from . import views

urlpatterns = [
    path('', views.statistics_dashboard, name='statistika'),
]