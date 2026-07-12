from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from dashboard.models import Task
from ibodat.models import PrayerLog
from quran.models import AyahMemorization

@login_required
def statistics_dashboard(request):
    user  = request.user
    today = timezone.localdate()

    # Oxirgi 30 kun
    days = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)

        # Namoz
        prayer_logs = PrayerLog.objects.filter(user=user, date=day)
        prayer_done = prayer_logs.filter(is_done=True).count()
        prayer_pct  = int((prayer_done / 5) * 100) if prayer_done else 0

        # Task
        tasks       = Task.objects.filter(user=user, due_date=day)
        task_total  = tasks.count()
        task_done   = tasks.filter(is_completed=True).count()
        task_pct    = int((task_done / task_total) * 100) if task_total > 0 else 0

        # =====================================================================
        # YANGI QO'SHILGAN QISM: Tasklarni nomma-nom ro'yxatga olish
        # =====================================================================
        day_tasks_list = []
        for t in tasks:
            day_tasks_list.append({
                'title': t.title,
                'category': t.get_category_display(),
                'is_completed': t.is_completed,
                'xp_reward': t.xp_reward
            })
        # =====================================================================

        # Quran
        quran_repeats = AyahMemorization.objects.filter(
            user=user, last_practiced__date=day
        ).count()
        quran_pct = min(quran_repeats * 10, 100)

        # Umumiy
        overall = int((prayer_pct + task_pct + quran_pct) / 3)

        days.append({
            'date':       day,
            'day_num':    day.day,
            'day_name':   day.strftime('%a'),
            'is_today':   day == today,
            'prayer_pct': prayer_pct,
            'prayer_done': prayer_done,
            'task_pct':   task_pct,
            'task_done':  task_done,
            'task_total': task_total,
            'tasks_list': day_tasks_list,  # <-- Ro'yxatni templatega yuboramiz
            'quran_pct':  quran_pct,
            'overall':    overall,
        })

    # Umumiy statistika
    total_prayers  = PrayerLog.objects.filter(user=user, is_done=True).count()
    total_tasks    = Task.objects.filter(user=user, is_completed=True).count()
    total_memorized = AyahMemorization.objects.filter(user=user, is_memorized=True).count()

    context = {
        'days':             days,
        'total_prayers':    total_prayers,
        'total_tasks':      total_tasks,
        'total_memorized':  total_memorized,
        'today':            today,
    }
    return render(request, 'statistika/dashboard.html', context)