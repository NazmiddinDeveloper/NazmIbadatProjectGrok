from django.db import models
from django.conf import settings

class AyahMemorization(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hifz_progress')
    surah_number = models.IntegerField()  # 1 dan 114 gacha
    ayah_number = models.IntegerField()   # Oyat raqami
    
    is_memorized = models.BooleanField(default=False)
    repeats = models.IntegerField(default=0)  # Tasbeh sanog'i
    
    # Ko'z xotirasi uchun Mushaf rasmi
    mushaf_image = models.ImageField(upload_to='mushaf_images/', null=True, blank=True)
    
    # Shaxsiy audio yuklash uchun (YANGI)
    custom_audio = models.FileField(upload_to='custom_audios/', null=True, blank=True)
    custom_audio_title = models.CharField(max_length=100, null=True, blank=True)
    
    last_practiced = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'surah_number', 'ayah_number']
        ordering = ['surah_number', 'ayah_number']

    def __str__(self):
        return f"{self.user.username} - Sura {self.surah_number}, Oyat {self.ayah_number}"
    
    # Ko'z xotirasi uchun Mushaf rasmi
    mushaf_image = models.ImageField(upload_to='mushaf_images/', null=True, blank=True)
    
    # Shaxsiy audio yuklash uchun (YANGI)
    custom_audio = models.FileField(upload_to='custom_audios/', null=True, blank=True)
    custom_audio_title = models.CharField(max_length=100, null=True, blank=True)