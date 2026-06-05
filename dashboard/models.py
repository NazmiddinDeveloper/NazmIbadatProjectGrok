from django.db import models
from django.conf import settings
from django.utils import timezone


class Task(models.Model):
    CATEGORY_CHOICES = (
        ('school21', 'School 21'),
        ('english',  'Ingliz tili'),
        ('uzum',     'Uzum'),
        ('other',    'Boshqa'),
    )
    PRIORITY_CHOICES = (
        ('high',   'Yuqori'),
        ('medium', "O'rta"),
        ('low',    'Past'),
    )

    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    title      = models.CharField(max_length=200)
    category   = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    priority   = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    due_date   = models.DateField(default=timezone.now)
    is_completed = models.BooleanField(default=False)
    xp_reward  = models.IntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Shift(models.Model):
    SHIFT_TYPES = (
        ('day',   'Kunduzgi'),
        ('night', 'Tungi'),
        ('off',   'Dam olish'),
    )
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shifts')
    date       = models.DateField()
    shift_type = models.CharField(max_length=10, choices=SHIFT_TYPES)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.user} | {self.date} | {self.shift_type}"