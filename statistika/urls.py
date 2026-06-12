from django.urls import path
from . import views

app_name = 'statistika'

urlpatterns = [
    path('', views.statistics_dashboard, name='dashboard'),
]