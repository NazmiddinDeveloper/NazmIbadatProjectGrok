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

'''path('hifz-test/', views.hifz_test_view, name='hifz_test'),
        path('api/hifz-review/', views.submit_hifz_review, name='submit_hifz_review'),
        path('api/hifz-mistake/add/', views.mark_mistake, name='add_mistake'),
        path('api/hifz-mistake/remove/', views.remove_mistake, name='remove_mistake'),'''
