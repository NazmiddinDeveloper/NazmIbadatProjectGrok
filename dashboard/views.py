from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import F
from .models import Task, Shift
from .forms import TaskForm
from ibodat.views import get_prayer_data
import calendar
from datetime import datetime

@login_required
def home(request):
    user = request.user
    today = timezone.localdate()

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = user
            task.save()
            return redirect('home')
    else:
        form = TaskForm()

    tasks = Task.objects.filter(user=user, due_date=today)
    completed = tasks.filter(is_completed=True).count()
    total = tasks.count()
    progress = int((completed / total) * 100) if total > 0 else 0

    shifts = Shift.objects.filter(user=user, date__gte=today)[:3]

    next_level_xp = user.level * 500
    level_progress = int((user.xp / next_level_xp) * 100) if next_level_xp > 0 else 0

    # === Namoz vaqtlari ===
    prayer_data = get_prayer_data()
    times_json = prayer_data['today']['times'] if prayer_data else {}
    current_key = prayer_data['today']['current']['key'] if prayer_data else None
    next_prayer = prayer_data['today']['next'] if prayer_data else {}

    from ibodat.models import PrayerLog
    from ibodat.views import build_prayers

    today_logs = PrayerLog.objects.filter(user=user, date=today)
    done_set = set(today_logs.filter(is_done=True).values_list('prayer', flat=True))
    done_at_map = {l.prayer: str(l.done_at)[:5] for l in today_logs if l.done_at}
    status_map = {l.prayer: l.status for l in today_logs}

    prayers_mini = build_prayers(times_json, current_key, done_set, done_at_map, status_map) if times_json else []

    # === QUYOSH CHIQISHI WIDGETI (faqat Bomdod vaqti ichida ko'rinadi) ===
    show_sunrise_widget = False
    quyosh_time = times_json.get('quyosh')

    if quyosh_time:
        try:
            now_str = timezone.localtime().strftime('%H:%M')
            now_dt = datetime.strptime(now_str, "%H:%M")
            quyosh_dt = datetime.strptime(quyosh_time, "%H:%M")

            if now_dt < quyosh_dt:
                show_sunrise_widget = True
        except:
            pass

    context = {
        'form': form,
        'tasks': tasks,
        'completed': completed,
        'total': total,
        'progress': progress,
        'shifts': shifts,
        'level_progress': level_progress,
        'next_level_xp': next_level_xp,
        'xp_remaining': next_level_xp - user.xp,
        'today': today,
        'times_json': times_json,
        'prayers_mini': prayers_mini,
        'next_prayer': next_prayer,
        'show_sunrise_widget': show_sunrise_widget,   # ← Qo'shildi
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def toggle_task(request, task_id):
    if request.method != 'POST':
        return redirect('home')

    task = get_object_or_404(Task, id=task_id, user=request.user)
    user = request.user

    if not task.is_completed:
        task.is_completed = True
        user.__class__.objects.filter(pk=user.pk).update(
            xp=F('xp') + task.xp_reward
        )
    else:
        task.is_completed = False
        user.__class__.objects.filter(pk=user.pk).update(
            xp=F('xp') - task.xp_reward
        )

    user.refresh_from_db()
    user.level = (user.xp // 500) + 1
    user.save(update_fields=['level'])

    task.save()
    return redirect('home')


@login_required
def delete_task(request, task_id):
    if request.method != 'POST':
        return redirect('home')

    task = get_object_or_404(Task, id=task_id, user=request.user)
    if task.is_completed:
        user = request.user
        user.__class__.objects.filter(pk=user.pk).update(
            xp=F('xp') - task.xp_reward
        )
        user.refresh_from_db()
        user.level = (user.xp // 500) + 1
        user.save(update_fields=['level'])

    task.delete()
    return redirect('home')


@login_required
def smenalar(request):
    today = timezone.localdate()

    if request.method == 'POST':
        shift_date = request.POST.get('date')
        shift_type = request.POST.get('shift_type')
        
        if shift_date:
            if shift_type == 'delete':
                Shift.objects.filter(user=request.user, date=shift_date).delete()
            elif shift_type in dict(Shift.SHIFT_TYPES).keys():
                Shift.objects.update_or_create(
                    user=request.user, 
                    date=shift_date,
                    defaults={'shift_type': shift_type}
                )
        
        # URL dagi bo'sh parametrlarni oldini olish (Redirect qilish)
        y = request.GET.get('year')
        m = request.GET.get('month')
        if y and m:
            return redirect(f"{request.path}?year={y}&month={m}")
        return redirect(request.path)

    # GET parametrlarini xavfsiz o'qish (bo'sh yoki matn bo'lsa xato bermaydi)
    y_str = request.GET.get('year')
    m_str = request.GET.get('month')
    
    try:
        year  = int(y_str) if y_str else today.year
        month = int(m_str) if m_str else today.month
    except ValueError:
        year  = today.year
        month = today.month

    # Kalendar yasash (Dushanbadan boshlanadi)
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)

    # Shu oydagi smenalarni bazadan olish
    start_date = month_days[0][0]
    end_date   = month_days[-1][-1]
    shifts = Shift.objects.filter(user=request.user, date__range=[start_date, end_date])
    shift_dict = {str(s.date): s.shift_type for s in shifts}

    cal_data = []
    for week in month_days:
        week_data = []
        for d in week:
            week_data.append({
                'date': str(d),
                'day': d.day,
                'is_current_month': d.month == month,
                'is_today': d == today,
                'shift': shift_dict.get(str(d))
            })
        cal_data.append(week_data)

    uz_months = {1:"Yanvar", 2:"Fevral", 3:"Mart", 4:"Aprel", 5:"May", 6:"Iyun", 
                 7:"Iyul", 8:"Avgust", 9:"Sentabr", 10:"Oktabr", 11:"Noyabr", 12:"Dekabr"}

    prev_month = month - 1 if month > 1 else 12
    prev_year  = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year  = year if month < 12 else year + 1

    context = {
        'calendar':   cal_data,
        'month_name': uz_months[month],
        'year':       year,
        'prev_month': prev_month, 'prev_year': prev_year,
        'next_month': next_month, 'next_year': next_year,
    }
    return render(request, 'dashboard/smenalar.html', context)
