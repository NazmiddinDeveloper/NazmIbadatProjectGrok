from datetime import datetime, timedelta
import requests

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from dashboard.models import Task
from .models import PrayerLog, PRAYER_ORDER, PRAYER_CHOICES
from .utils import get_prayer_zones, get_done_status

# === API VA DOIMIY SOZLAMALAR ===
PRAYER_API = "https://namoz-vaqti.uz"

# API da Tahajjud bo'lmagani uchun ichki tartibni alohida belgilaymiz
LOCAL_PRAYER_ORDER = ['tahajjud', 'bomdod', 'peshin', 'asr', 'shom', 'xufton']

PRAYER_LABELS = {
    'tahajjud': 'Tahajjud',
    'bomdod': 'Bomdod',
    'peshin': 'Peshin',
    'asr': 'Asr',
    'shom': 'Shom',
    'xufton': 'Xufton'
}

PRAYER_ICONS = {
    'tahajjud': '🌌',
    'bomdod': '🌙',
    'peshin': '☀️',
    'asr': '🌤',
    'shom': '🌆',
    'xufton': '🌃'
}


def get_prayer_data():
    """Keshdan namoz vaqtlarini qidiradi, bo'lmasa API orqali yuklaydi."""
    data = cache.get('prayer_data_today')
    if not data:
        try:
            r = requests.get(PRAYER_API, timeout=6)
            r.raise_for_status()
            data = r.json()
            cache.set('prayer_data_today', data, timeout=43200)  # 12 soatga keshlanadi
        except Exception as e:
            print(f"Prayer API Error: {e}")
            return None
    return data


def build_prayers(times, current_key, done_set, done_at_map, status_map):
    """Namozlar ro'yxatini va ularning joriy holatlarini (zonalarni) shakllantiradi."""
    prayer_keys = LOCAL_PRAYER_ORDER
    result = []
    now_str = timezone.localtime().strftime('%H:%M')
    now_dt = datetime.strptime(now_str, "%H:%M")

    for i, key in enumerate(prayer_keys):
        # Tahajjud uchun maxsus vaqt oralig'i (02:00 dan Bomdodgacha)
        if key == 'tahajjud':
            start = '02:00'
            end = times.get('bomdod', '05:00')
        else:
            start = times.get(key, '00:00')
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
        if key == current_key and not is_done:
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
    """Asosiy ibodat sahifasi: bugungi namozlar, streak va haftalik statistika."""
    today = timezone.localdate()
    data = get_prayer_data()

    times = {}
    current = {}
    next_p = {}

    if data:
        times = data['today']['times']
        current = data['today']['current']
        next_p = data['today']['next']

    # Foydalanuvchining bugungi loglari
    logs = PrayerLog.objects.filter(user=request.user, date=today)
    done_set = set(logs.filter(is_done=True).values_list('prayer', flat=True))
    done_at_map = {l.prayer: str(l.done_at)[:5] for l in logs if l.done_at}
    status_map = {l.prayer: l.status for l in logs}

    prayers = build_prayers(times, current.get('key'), done_set, done_at_map, status_map)

    # === Streak hisoblash (Faqat 5 vaqt farz namozlari asosida) ===
    streak = 0
    check_date = today - timedelta(days=1)
    obligatory = ['bomdod', 'peshin', 'asr', 'shom', 'xufton']
    
    while True:
        day_logs = PrayerLog.objects.filter(
            user=request.user, date=check_date, is_done=True, prayer__in=obligatory
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
            user=request.user, date=day, is_done=True, prayer__in=obligatory
        ).count()
        week_data.append({
            'day': day.strftime('%a'),
            'date': str(day),
            'count': count,
            'pct': int((count / 5) * 100),
        })

    done_today = len(done_set)

    # === QUYOSH WIDGETI ===
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
    """Namoz holatini o'zgartirish (bajarildi/bajarilmadi) uchun POST so'rovi."""
    if request.method != 'POST':
        return redirect('ibodat')

    date_str = request.POST.get('date')
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = timezone.localdate()
    else:
        target_date = timezone.localdate()

    now = timezone.localtime().strftime('%H:%M')
    
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
    return redirect(request.META.get('HTTP_REFERER', 'ibodat'))


@login_required
def history(request):
    """30 kunlik kalendar ko'rinishidagi tarix va kunlik progress foizlari (XP)."""
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

    # 30 kunlik kalendar tuzish
    today = timezone.localdate()
    calendar = []
    obligatory = ['bomdod', 'peshin', 'asr', 'shom', 'xufton']

    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        
        day_logs = PrayerLog.objects.filter(user=request.user, date=day)
        log_dict = {l.prayer: l.status for l in day_logs}

        is_ruined = False
        all_prayers_perfect = True
        prayer_dots = []
        
        p_score = 0
        tahajjud_bonus = 0

        # === TAHAJJUD TEKSHIRUVI (Maxsus bonus XP) ===
        tahajjud_status = log_dict.get('tahajjud', 'missed')
        if tahajjud_status in ['on_time', 'jamoat', 'late', 'makruh']:
            prayer_dots.append('tahajjud_done')
            tahajjud_bonus = 20  # Progressga qo'shiladigan alohida bonus
            
        # === FARZ NAMOZLARINI TEKSHIRUVI ===
        for p in obligatory:
            st = log_dict.get(p, 'missed')
            prayer_dots.append(st)

            if st == 'missed':
                is_ruined = True

            if st not in ['on_time', 'jamoat']:
                all_prayers_perfect = False

            if st == 'jamoat':
                p_score += 15
            elif st == 'on_time':
                p_score += 10
            elif st == 'late':
                p_score += 7
            elif st == 'qaza':
                p_score += 3

        # Farz namozlardan to'plangan foiz (Maksimal 50 ball asosida)
        base_pct = (p_score / 50) * 100
        
        # Tahajjud bonusi qo'shiladi, lekin umumiy progress 100% dan oshmaydi
        p_pct = min(base_pct + tahajjud_bonus, 100)

        calendar.append({
            'date': day,
            'day_str': day.strftime('%d'),
            'dots': prayer_dots,
            'is_ruined': is_ruined,
            'perfect': all_prayers_perfect,
            'pct': int(p_pct),
            'is_selected': day == selected_date,
        })

    context = {
        'selected_date': selected_date,
        'prayers': prayers,
        'calendar': calendar,
    }
    return render(request, 'ibodat/history.html', context)
