from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    xp     = models.IntegerField(default=0)
    level  = models.IntegerField(default=1)
    streak = models.IntegerField(default=0)

    def add_xp(self, amount):
        self.xp += amount
        self.level = (self.xp // 500) + 1
        self.save(update_fields=['xp', 'level'])

    def __str__(self):
        return self.username