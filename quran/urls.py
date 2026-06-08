from django.urls import path
from . import views

urlpatterns = [
    path('', views.quran_home, name='quran_home'),
    path('surah/<int:surah_id>/', views.surah_detail, name='surah_detail'),
    path('memorize/<int:surah_id>/<int:ayah_id>/', views.memorize_ayah, name='memorize_ayah'),
    path('api/repeat/<int:surah_id>/<int:ayah_id>/', views.api_repeat, name='api_repeat'),
    path('api/memorize/<int:surah_id>/<int:ayah_id>/', views.api_memorize, name='api_memorize'),
    path('api/upload-image/<int:surah_id>/<int:ayah_id>/', views.api_upload_image, name='api_upload_image'),
]