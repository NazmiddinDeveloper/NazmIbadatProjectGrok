from django.db import models
from django.conf import settings
from django.utils import timezone


PRAYER_CHOICES = (
    ('bomdod', 'Bomdod'),
    ('peshin', 'Peshin'),
    ('asr',    'Asr'),
    ('shom',   'Shom'),
    ('xufton', 'Xufton'),
)

PRAYER_ORDER = ['bomdod', 'peshin', 'asr', 'shom', 'xufton']


class PrayerTime(models.Model):
    date   = models.DateField()
    prayer = models.CharField(max_length=10, choices=PRAYER_CHOICES)
    time   = models.TimeField()

    class Meta:
        unique_together = ['date', 'prayer']
        ordering        = ['date', 'time']

    def __str__(self):
        return f"{self.date} | {self.prayer} | {self.time}"


class PrayerLog(models.Model):
    STATUS_CHOICES = (
        ('on_time', 'Boshida'),   # Yashil
        ('late',    'O\'rtasida'), # Sariq
        ('makruh',  'Oxirida'),   # Qizil (Qazo emas!)
        ('qaza',    'Qazo'),      # Qora (Vaqti o'tib ketgan)
        ('missed',  'O\'tkazib'), # O'qilmagan
    )

    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prayer_logs'
    )
    date       = models.DateField()
    prayer     = models.CharField(max_length=10, choices=PRAYER_CHOICES)
    is_done    = models.BooleanField(default=False)
    done_at    = models.TimeField(null=True, blank=True)  # qaysi vaqtda bajarildi
    status     = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='missed'
    )

    class Meta:
        unique_together = ['user', 'date', 'prayer']
        ordering        = ['date', 'prayer']

    def __str__(self):
        return f"{self.user} | {self.date} | {self.prayer} | {self.status}"