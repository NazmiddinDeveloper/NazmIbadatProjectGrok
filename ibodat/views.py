from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import PrayerLog, PRAYER_ORDER, PRAYER_CHOICES
from .utils import get_prayer_zones, get_done_status
from dashboard.models import Task
from django.core.cache import cache
import requests


PRAYER_API = "https://namoz-vaqti.uz/index.php?format=json&region=toshkent-shahri&period=today"

PRAYER_LABELS = {
    'bomdod': 'Bomdod',
    'peshin': 'Peshin',
    'asr': 'Asr',
    'shom': 'Shom',
    'xufton': 'Xufton'
}

PRAYER_ICONS = {
    'bomdod': '🌙',
    'peshin': '☀️',
    'asr': '🌤',
    'shom': '🌆',
    'xufton': '🌃'
}


def get_prayer_data():
    # Keshdan 'prayer_data_today' degan kalit bilan qidiramiz
    data = cache.get('prayer_data_today')
    
    if not data:
        # Agar keshda bo'lmasa, API ga murojaat qilamiz
        try:
            r = requests.get(PRAYER_API, timeout=6)
            r.raise_for_status()
            data = r.json()
            # Ma'lumotni keshga saqlaymiz (masalan, 12 soatga - 43200 soniya)
            cache.set('prayer_data_today', data, timeout=43200)
        except Exception as e:
            print(f"Prayer API Error: {e}")
            return None
    return data


def build_prayers(times, current_key, done_set, done_at_map, status_map):
    prayer_keys = PRAYER_ORDER
    result = []
    now_str = timezone.localtime().strftime('%H:%M')
    now_dt = datetime.strptime(now_str, "%H:%M")

    for i, key in enumerate(prayer_keys):
        start = times.get(key, '00:00')

        # Bomdod uchun maxsus tugash vaqti (Quyosh)
        if key == 'bomdod':
            end = times.get('quyosh', '06:30')
        else:
            end = times.get(prayer_keys[i + 1], '23:59') if i + 1 < len(prayer_keys) else '23:59'

        zones = get_prayer_zones(start, end)
        is_done = key in done_set
        status = status_map.get(key, 'missed')
        done_at = done_at_map.get(key)

        start_dt = datetime.strptime(start, "%H:%M")
        end_dt = datetime.strptime(end, "%H:%M")

        is_pending = False
        needs_modal = False

        if not is_done:
            if now_dt < start_dt:
                is_pending = True
                status = 'pending'
            elif now_dt > end_dt:
                needs_modal = True
                status = 'missed'

        zone_color = 'green'
        if key == current_key:
            green_end = datetime.strptime(zones['green']['to'], "%H:%M")
            yellow_end = datetime.strptime(zones['yellow']['to'], "%H:%M")
            if now_dt > yellow_end:
                zone_color = 'red'
            elif now_dt > green_end:
                zone_color = 'yellow'

        result.append({
            'key': key,
            'label': PRAYER_LABELS[key],
            'icon': PRAYER_ICONS[key],
            'time': start,
            'end': end,
            'zones': zones,
            'is_done': is_done,
            'done_at': done_at,
            'status': status,
            'current': key == current_key,
            'zone_color': zone_color,
            'is_pending': is_pending,
            'needs_modal': needs_modal,
        })

    return result


@login_required
def ibodat(request):
    today = timezone.localdate()
    data = get_prayer_data()

    times = {}
    current = {}
    next_p = {}

    if data:
        times = data['today']['times']
        current = data['today']['current']
        next_p = data['today']['next']

    # Foydalanuvchi loglari
    logs = PrayerLog.objects.filter(user=request.user, date=today)
    done_set = set(logs.filter(is_done=True).values_list('prayer', flat=True))
    done_at_map = {l.prayer: str(l.done_at)[:5] for l in logs if l.done_at}
    status_map = {l.prayer: l.status for l in logs}

    prayers = build_prayers(times, current.get('key'), done_set, done_at_map, status_map)

    # === Streak hisoblash ===
    streak = 0
    check_date = today - timedelta(days=1)
    while True:
        day_logs = PrayerLog.objects.filter(
            user=request.user, date=check_date, is_done=True
        )
        if day_logs.count() >= 5:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    # === Haftalik statistika ===
    week_start = today - timedelta(days=6)
    week_data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        count = PrayerLog.objects.filter(
            user=request.user, date=day, is_done=True
        ).count()
        week_data.append({
            'day': day.strftime('%a'),
            'date': str(day),
            'count': count,
            'pct': int((count / 5) * 100),
        })

    done_today = len(done_set)

    # === QUYOSH WIDGETI (faqat Bomdod vaqti ichida ko'rinadi) ===
    show_sunrise = False
    quyosh_time = times.get('quyosh')

    if quyosh_time:
        try:
            now_str = timezone.localtime().strftime('%H:%M')
            now_dt = datetime.strptime(now_str, "%H:%M")
            quyosh_dt = datetime.strptime(quyosh_time, "%H:%M")

            if now_dt < quyosh_dt:
                show_sunrise = True
        except:
            pass

    context = {
        'prayers': prayers,
        'current': current,
        'next_p': next_p,
        'today': today,
        'times_json': times,
        'streak': streak,
        'week_data': week_data,
        'done_today': done_today,
        'show_sunrise': show_sunrise,
        'quyosh_time': quyosh_time,
    }
    return render(request, 'ibodat/ibodat.html', context)


@login_required
def toggle_prayer(request, prayer_key):
    if request.method != 'POST':
        return redirect('ibodat')

    # Formadan sana kelsa o'qib olamiz, kelmasa bugungi kunni olamiz
    date_str = request.POST.get('date')
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = timezone.localdate()
    else:
        target_date = timezone.localdate()

    now = timezone.localtime().strftime('%H:%M')
    
    # target_date bo'yicha bazadan qidiramiz yoki yaratamiz
    log, _ = PrayerLog.objects.get_or_create(
        user=request.user, date=target_date, prayer=prayer_key
    )

    manual_status = request.POST.get('manual_status')
    
    if manual_status == 'cancel':
        log.is_done = False
        log.done_at = None
        log.status = 'missed'
    elif manual_status:
        log.is_done = True
        if not log.done_at:
            log.done_at = now
        log.status = manual_status
        
    log.save()
    # Qaysi sahifadan kelgan bo'lsa (ibodat yoki tarix), o'sha sahifaga qaytaradi
    return redirect(request.META.get('HTTP_REFERER', 'ibodat'))

@login_required
def history(request):
    selected_date_str = request.GET.get('date', str(timezone.localdate()))

    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = timezone.localdate()

    data = get_prayer_data()
    times = data['today']['times'] if data else {}
    current_key = data['today']['current']['key'] if data and selected_date == timezone.localdate() else None

    logs = PrayerLog.objects.filter(user=request.user, date=selected_date)
    done_set = set(logs.filter(is_done=True).values_list('prayer', flat=True))
    done_at_map = {l.prayer: str(l.done_at)[:5] for l in logs if l.done_at}
    status_map = {l.prayer: l.status for l in logs}

    prayers = build_prayers(times, current_key, done_set, done_at_map, status_map)

    # 30 kunlik kalendar
    today = timezone.localdate()
    calendar = []
    obligatory = ['bomdod', 'peshin', 'asr', 'shom', 'xufton']

    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        is_past_day = day < today

        day_logs = PrayerLog.objects.filter(user=request.user, date=day)
        log_dict = {l.prayer: l.status for l in day_logs}

        is_ruined = False
        all_prayers_perfect = True
        prayer_dots = []
        p_score = 0

        for p in obligatory:
            st = log_dict.get(p, 'missed')
            prayer_dots.append(st)
            if st == 'missed':
                is_ruined = True
            if st not in ['on_time', 'jamoat']:  # Jamoat ham perfect hisoblanadi
                all_prayers_perfect = False
                
            if st == 'jamoat':
                p_score += 15  # Jamoat uchun BONUS ball!
            elif st == 'on_time':
                p_score += 10
            elif st == 'late':
                p_score += 7
            elif st == 'qaza':
                p_score += 3

        p_pct = (p_score / 50) * 100

        day_tasks = Task.objects.filter(user=request.user, due_date=day)
        total_tasks = day_tasks.count()
        completed_tasks = day_tasks.filter(is_completed=True).count()
        task_pct = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 100

        all_tasks_perfect = (total_tasks > 0 and completed_tasks == total_tasks) or (total_tasks == 0)

        efficiency = int((p_pct + task_pct) / 2)

        day_status = 'normal'
        if is_past_day:
            if is_ruined:
                day_status = 'ruined'
            elif all_prayers_perfect and all_tasks_perfect and p_score == 50:
                day_status = 'perfect'

        calendar.append({
            'date': str(day),
            'day_num': day.day,
            'day_name': day.strftime('%a'),
            'prayer_dots': prayer_dots,
            'task_pct': task_pct,
            'total_tasks': total_tasks,
            'efficiency': efficiency,
            'status': day_status,
            'selected': str(day) == str(selected_date),
        })

    # === QUYOSH VAQTI (history sahifasi uchun) ===
    show_sunrise = False
    quyosh_time = times.get('quyosh')

    if quyosh_time:
        try:
            now_str = timezone.localtime().strftime('%H:%M')
            now_dt = datetime.strptime(now_str, "%H:%M")
            quyosh_dt = datetime.strptime(quyosh_time, "%H:%M")

            if now_dt < quyosh_dt:
                show_sunrise = True
        except:
            pass

    context = {
        'prayers': prayers,
        'selected_date': selected_date,
        'calendar': calendar,
        'times_json': times,
        'today': today,
        'show_sunrise': show_sunrise,      # ← Qo‘shildi
        'quyosh_time': quyosh_time,        # ← Qo‘shildi
    }
    return render(request, 'ibodat/history.html', context)