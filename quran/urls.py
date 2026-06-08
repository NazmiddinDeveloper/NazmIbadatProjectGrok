from django.urls import path
from . import views

urlpatterns = [
    path('', views.quran_home, name='quran_home'),
    path('surah/<int:surah_id>/', views.surah_detail, name='surah_detail'),
    path('memorize/<int:surah_id>/<int:ayah_id>/', views.memorize_ayah, name='memorize_ayah'),
]