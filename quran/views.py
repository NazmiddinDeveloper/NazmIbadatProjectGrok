import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from .models import AyahMemorization
from .tajvid import colorize_arabic
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
def quran_home(request):
    """Barcha suralar ro'yxati va umumiy yodlash statistikasi"""
    try:
        r = requests.get('https://api.alquran.cloud/v1/surah', timeout=5)
        surahs = r.json()['data']
    except:
        surahs = []

    memorized_count = AyahMemorization.objects.filter(
        user=request.user, is_memorized=True
    ).count()
    total_ayahs  = 6236
    progress_pct = int((memorized_count / total_ayahs) * 100) if total_ayahs > 0 else 0

    context = {
        'surahs':          surahs,
        'memorized_count': memorized_count,
        'total_ayahs':     total_ayahs,
        'progress_pct':    progress_pct,
    }
    return render(request, 'quran/home.html', context)


@login_required
def surah_detail(request, surah_id):
    """Sura ichidagi barcha oyatlar va ularning yodlanish holati"""
    try:
        r = requests.get(
            f'https://api.alquran.cloud/v1/surah/{surah_id}/quran-uthmani',
            timeout=5
        )
        surah_data = r.json()['data']
    except:
        return redirect('quran_home')

    progress = AyahMemorization.objects.filter(
        user=request.user, surah_number=surah_id
    )
    memo_dict = {p.ayah_number: p for p in progress}

    ayahs = []
    for ayah in surah_data['ayahs']:
        num = ayah['numberInSurah']
        p   = memo_dict.get(num)
        ayahs.append({
            'number':       num,
            'text':         ayah['text'],
            'text_colored': mark_safe(colorize_arabic(ayah['text'])),
            'is_memorized': p.is_memorized if p else False,
            'repeats':      p.repeats if p else 0,
        })

    context = {
        'surah': surah_data,
        'ayahs': ayahs,
    }
    return render(request, 'quran/surah_detail.html', context)


@login_required
def memorize_ayah(request, surah_id, ayah_id):
    """Yodlash xonasi — bitta oyat, uning audiolari va takrorlar soni"""
    try:
        r = requests.get(
            f'https://api.alquran.cloud/v1/ayah/{surah_id}:{ayah_id}/quran-uthmani',
            timeout=5
        )
        ayah_data = r.json()['data']
    except:
        return redirect('surah_detail', surah_id=surah_id)

    # 1. Maher Al-Muaiqly audiosi (Identifikator to'g'rilandi: ar.maheralmuaiqly)
    audio_url_muaiqly = ''
    try:
        r3 = requests.get(
            f'https://api.alquran.cloud/v1/ayah/{surah_id}:{ayah_id}/ar.mahermuaiqly',
            timeout=5
        )
        if r3.status_code == 200:
            audio_url_muaiqly = r3.json()['data'].get('audio', '')
    except:
        pass

    # 2. Mishary Al-Afasy audiosi
    audio_url = ''
    try:
        r2 = requests.get(
            f'https://api.alquran.cloud/v1/ayah/{surah_id}:{ayah_id}/ar.alafasy',
            timeout=5
        )
        if r2.status_code == 200:
            audio_url = r2.json()['data'].get('audio', '')
    except:
        pass

    obj, _ = AyahMemorization.objects.get_or_create(
        user=request.user,
        surah_number=surah_id,
        ayah_number=ayah_id,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'repeat':
            obj.repeats += 1
            obj.save(update_fields=['repeats'])
        elif action == 'memorized':
            obj.is_memorized = True
            obj.repeats += 1
            obj.save(update_fields=['is_memorized', 'repeats'])
            return redirect('surah_detail', surah_id=surah_id)
        elif action == 'unmemorize':
            obj.is_memorized = False
            obj.save(update_fields=['is_memorized'])
        return redirect('memorize_ayah', surah_id=surah_id, ayah_id=ayah_id)

    context = {
        'surah_id':     surah_id,
        'ayah_id':      ayah_id,
        'ayah_text':    ayah_data.get('text', ''),
        'text_colored': mark_safe(colorize_arabic(ayah_data.get('text', ''))),
        'surah_name':   ayah_data.get('surah', {}).get('englishName', ''),
        'surah_arabic': ayah_data.get('surah', {}).get('name', ''),
        'total_ayahs':  ayah_data.get('surah', {}).get('numberOfAyahs', 0),
        'audio_url':    audio_url,
        'obj':          obj,
        'prev_ayah':    ayah_id - 1 if ayah_id > 1 else None,
        'next_ayah':    ayah_id + 1 if ayah_id < ayah_data.get('surah', {}).get('numberOfAyahs', 0) else None,
        'audio_url_muaiqly': audio_url_muaiqly,
    }
    return render(request, 'quran/memorize.html', context)


@login_required
@require_POST
def api_repeat(request, surah_id, ayah_id):
    """AJAX — sahifa yangilanmay takror sonini +1 qiladi"""
    obj, _ = AyahMemorization.objects.get_or_create(
        user=request.user,
        surah_number=surah_id,
        ayah_number=ayah_id,
    )
    obj.repeats += 1
    obj.save(update_fields=['repeats'])
    return JsonResponse({'repeats': obj.repeats, 'status': 'ok'})


@login_required
@require_POST
def api_memorize(request, surah_id, ayah_id):
    """AJAX — yodlandi/yodlanmadi toggle"""
    obj, _ = AyahMemorization.objects.get_or_create(
        user=request.user,
        surah_number=surah_id,
        ayah_number=ayah_id,
    )
    obj.is_memorized = not obj.is_memorized
    if obj.is_memorized:
        obj.repeats += 1
    obj.save(update_fields=['is_memorized', 'repeats'])
    return JsonResponse({
        'is_memorized': obj.is_memorized,
        'repeats':      obj.repeats,
        'status':       'ok'
    })


@login_required
@require_POST
def api_upload_image(request, surah_id, ayah_id):
    """AJAX — oyat mushaf rasmini yuklash"""
    if 'image' not in request.FILES:
        return JsonResponse({'status': 'error', 'msg': 'Rasm yo\'q'}, status=400)

    obj, _ = AyahMemorization.objects.get_or_create(
        user=request.user,
        surah_number=surah_id,
        ayah_number=ayah_id,
    )
    obj.mushaf_image = request.FILES['image']
    obj.save(update_fields=['mushaf_image'])
    return JsonResponse({
        'status':    'ok',
        'image_url': obj.mushaf_image.url
    })
