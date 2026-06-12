from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import DailyStat

@login_required
def statistics_dashboard(request):
    user = request.user
    today = timezone.localdate()
    start_date = today - timedelta(days=30)

    # Oxirgi 30 kunlik ma'lumot
    stats = DailyStat.objects.filter(
        user=user,
        date__gte=start_date
    ).order_by('date')

    # Agar ma'lumot bo'lmasa, bo'sh ro'yxat
    if not stats.exists():
        context = {
            'has_data': False,
            'labels': [],
            'task_data': [],
            'quran_data': [],
            'overall_data': [],
        }
        return render(request, 'statistika/dashboard.html', context)

    labels = [s.date.strftime('%d.%m') for s in stats]
    task_data = [float(s.task_efficiency) for s in stats]
    quran_data = [float(s.quran_efficiency) for s in stats]
    overall_data = [float(s.overall_efficiency) for s in stats]

    context = {
        'has_data': True,
        'labels': labels,
        'task_data': task_data,
        'quran_data': quran_data,
        'overall_data': overall_data,
        'latest_stat': stats.last(),
        'stats_count': stats.count(),
    }
    return render(request, 'statistika/dashboard.html', context)