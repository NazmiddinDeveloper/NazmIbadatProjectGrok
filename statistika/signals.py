from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from dashboard.models import Task
from quran.models import AyahMemorization
from .services import calculate_daily_efficiency


@receiver(post_save, sender=Task)
def update_stat_on_task_change(sender, instance, **kwargs):
    if instance.due_date:
        calculate_daily_efficiency(instance.user, instance.due_date)


@receiver(post_save, sender=AyahMemorization)
def update_stat_on_quran_change(sender, instance, **kwargs):
    if instance.last_practiced:
        target_date = instance.last_practiced.date()
        calculate_daily_efficiency(instance.user, target_date)