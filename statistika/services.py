from datetime import date
from django.db.models import Sum
from dashboard.models import Task
from quran.models import AyahMemorization
from .models import DailyStat

def calculate_daily_efficiency(user, target_date: date):
    """Task va Qur'on bo'yicha samaradorlikni hisoblaydi (Variant A)"""

    # === TASK ===
    tasks = Task.objects.filter(user=user, due_date=target_date)
    task_total = tasks.count()
    task_completed = tasks.filter(is_completed=True).count()
    task_eff = round((task_completed / task_total) * 100, 1) if task_total > 0 else 0

    # === QUR'ON (Variant A) ===
    quran_logs = AyahMemorization.objects.filter(
        user=user, 
        last_practiced__date=target_date
    )

    # Har bir takror = 1 ball
    quran_repeats = quran_logs.aggregate(total=Sum('repeats'))['total'] or 0

    # Har bir yangi yodlangan oyat = 5 ball
    quran_new_memorized = quran_logs.filter(is_memorized=True).count()

    # Umumiy ball (maksimal 100)
    total_quran_points = quran_repeats + (quran_new_memorized * 5)
    quran_eff = min(round(total_quran_points, 1), 100)

    # === OVERALL ===
    overall = round((task_eff + quran_eff) / 2, 1)

    stat, created = DailyStat.objects.update_or_create(
        user=user,
        date=target_date,
        defaults={
            'task_efficiency': task_eff,
            'task_completed': task_completed,
            'task_total': task_total,
            'quran_efficiency': quran_eff,
            'quran_repeats': quran_repeats,
            'quran_memorized': quran_new_memorized,
            'overall_efficiency': overall,
        }
    )
    return stat