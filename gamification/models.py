from django.db import models
from django.conf import settings
from django.utils import timezone


class Badge(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    icon        = models.CharField(max_length=100)
    condition   = models.CharField(max_length=50, unique=True)
    xp_bonus    = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class UserBadge(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='earned_badges')
    badge      = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.user.username} — {self.badge.name}"
    

class DailyQuest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('completed', 'Bajarildi'),
        ('failed', 'Bajarilmadi'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_quests')
    date = models.DateField(default=timezone.localdate)
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_type = models.CharField(max_length=50)   # 'prayer', 'task', 'hifz', 'streak'
    target_value = models.IntegerField(default=1)
    current_progress = models.IntegerField(default=0)
    
    xp_reward = models.IntegerField(default=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    is_auto_generated = models.BooleanField(default=True)  # Avto yoki admin tomonidan
    motivational_message = models.TextField(blank=True)    # Xavotir yoki hamd xabari

    class Meta:
        unique_together = ('user', 'date', 'target_type')
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} | {self.date} | {self.title}"
    



class DailyQuest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('completed', 'Bajarildi'),
        ('failed', 'Bajarilmadi'),
    )

    TARGET_TYPES = (
        ('prayer', 'Namoz'),
        ('task', 'Vazifa'),
        ('hifz', 'Qur\'on yodlash'),
        ('streak', 'Streak saqlash'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='daily_quests'
    )
    date = models.DateField(default=timezone.localdate)
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES)
    target_value = models.IntegerField(default=1)
    current_progress = models.IntegerField(default=0)
    
    xp_reward = models.IntegerField(default=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    is_auto_generated = models.BooleanField(default=True)
    motivational_message = models.TextField(blank=True)   # Xavotir yoki rag‘batlantiruvchi xabar

    class Meta:
        unique_together = ('user', 'date', 'target_type')
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} | {self.date} | {self.title}"

    @property
    def progress_percent(self):
        if self.target_value == 0:
            return 100
        return min(int((self.current_progress / self.target_value) * 100), 100)