# statistika/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class DailyStat(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)

    # Task efficiency (0-100)
    task_efficiency = models.FloatField(default=0)
    task_completed = models.IntegerField(default=0)
    task_total = models.IntegerField(default=0)

    # Quran efficiency (0-100)
    quran_efficiency = models.FloatField(default=0)
    quran_repeats = models.IntegerField(default=0)      # Kunlik takrorlar
    quran_memorized = models.IntegerField(default=0)    # Kunlik yodlangan oyatlar

    overall_efficiency = models.FloatField(default=0)   # (task + quran) / 2

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']