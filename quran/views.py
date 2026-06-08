import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import AyahMemorization

@login_required
def quran_home(request):
    # API orqali 114 ta sura ro'yxatini olish
    try:
        r = requests.get('https://api.alquran.cloud/v1/surah', timeout=5)
        surahs = r.json()['data']
    except:
        surahs = []

    # Foydalanuvchining yodlagan oyatlari statistikasini olish
    memorized_count = AyahMemorization.objects.filter(user=request.user, is_memorized=True).count()
    total_ayahs = 6236
    progress_pct = int((memorized_count / total_ayahs) * 100) if total_ayahs > 0 else 0

    context = {
        'surahs': surahs,
        'memorized_count': memorized_count,
        'total_ayahs': total_ayahs,
        'progress_pct': progress_pct,
    }
    return render(request, 'quran/home.html', context)

@login_required
def surah_detail(request, surah_id):
    # API orqali sura va uning Usmoniy (Madina Mushafi) oyatlarini tortib kelish
    try:
        r = requests.get(f'https://api.alquran.cloud/v1/surah/{surah_id}/quran-uthmani', timeout=5)
        surah_data = r.json()['data']
    except:
        return redirect('quran_home')

    # Foydalanuvchining shu suradagi progressini bazadan olish
    progress = AyahMemorization.objects.filter(user=request.user, surah_number=surah_id)
    memo_dict = {p.ayah_number: p for p in progress}

    ayahs = []
    for ayah in surah_data['ayahs']:
        num = ayah['numberInSurah']
        p = memo_dict.get(num)
        ayahs.append({
            'number': num,
            'text': ayah['text'],
            'is_memorized': p.is_memorized if p else False,
            'repeats': p.repeats if p else 0,
        })

    context = {
        'surah': surah_data,
        'ayahs': ayahs,
    }
    return render(request, 'quran/surah_detail.html', context)

@login_required
def memorize_ayah(request, surah_id, ayah_id):
    # Bu qismni keyingi qadamda yozamiz
    pass