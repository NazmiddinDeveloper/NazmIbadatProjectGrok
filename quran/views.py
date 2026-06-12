from gamification.services import check_and_award_badges, update_quest_progress
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from .models import AyahMemorization
from .tajvid import colorize_arabic
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from gamification.services import update_quest_progress

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
    try:
        r_info = requests.get(f'https://api.alquran.cloud/v1/surah/{surah_id}', timeout=5)
        surah_data = r_info.json()['data']
        # Aniq Tajvid API (Quran.com)
        r_tajweed = requests.get(f'https://api.quran.com/api/v4/quran/verses/uthmani_tajweed?chapter_number={surah_id}', timeout=5)
        tajweed_data = r_tajweed.json()['verses']
    except:
        return redirect('quran_home')

    progress = AyahMemorization.objects.filter(user=request.user, surah_number=surah_id)
    memo_dict = {p.ayah_number: p for p in progress}

    ayahs = []
    for i, ayah in enumerate(surah_data['ayahs']):
        num = ayah['numberInSurah']
        p   = memo_dict.get(num)
        
        tajweed_html = tajweed_data[i]['text_uthmani_tajweed'] if i < len(tajweed_data) else ayah['text']
        
        ayahs.append({
            'number':       num,
            'text_colored': mark_safe(tajweed_html),
            'is_memorized': p.is_memorized if p else False,
            'repeats':      p.repeats if p else 0,
        })

    return render(request, 'quran/surah_detail.html', {'surah': surah_data, 'ayahs': ayahs})


@login_required
def memorize_ayah(request, surah_id, ayah_id):
    try:
        r = requests.get(f'https://api.alquran.cloud/v1/ayah/{surah_id}:{ayah_id}/quran-uthmani', timeout=5)
        ayah_data = r.json()['data']
        
        r_taj = requests.get(f'https://api.quran.com/api/v4/quran/verses/uthmani_tajweed?verse_key={surah_id}:{ayah_id}', timeout=5)
        tajweed_html = r_taj.json()['verses'][0]['text_uthmani_tajweed']
        
        # Transkripsiyani tortib kelish
        r_trans = requests.get(f'https://api.alquran.cloud/v1/ayah/{surah_id}:{ayah_id}/en.transliteration', timeout=5)
        transliteration = r_trans.json()['data']['text']
    except:
        return redirect('surah_detail', surah_id=surah_id)

    audio_url = f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{ayah_data['number']}.mp3"
    audio_url_muaiqly = f"https://cdn.islamic.network/quran/audio/128/ar.mahermuaiqly/{ayah_data['number']}.mp3"

    obj, _ = AyahMemorization.objects.get_or_create(user=request.user, surah_number=surah_id, ayah_number=ayah_id)
    # Memorize qilinganda:
    if obj.is_memorized:
        update_quest_progress(request.user, 'hifz', amount=1)
        
    if request.method == 'POST':
        action = request.POST.get('action')
        if 'custom_audio' in request.FILES:
            obj.custom_audio = request.FILES['custom_audio']
            obj.custom_audio_title = request.POST.get('audio_title', 'Mening audim')
            obj.save()
            check_and_award_badges(request.user)
        elif action == 'repeat':
            obj.repeats += 1
            obj.save(update_fields=['repeats'])
            check_and_award_badges(request.user)
        elif action == 'memorized':
            obj.is_memorized = True
            obj.repeats += 1
            obj.save(update_fields=['is_memorized', 'repeats'])
            check_and_award_badges(request.user)
            return redirect('surah_detail', surah_id=surah_id)
        elif action == 'unmemorize':
            obj.is_memorized = False
            obj.save(update_fields=['is_memorized'])
            check_and_award_badges(request.user)
        elif action == 'delete_image':
            if obj.mushaf_image:
                obj.mushaf_image.delete()
            return redirect('memorize_ayah', surah_id=surah_id, ayah_id=ayah_id)
        elif action == 'save_tafsir':
            obj.tafsir_text = request.POST.get('tafsir_text')
            obj.tafsir_author = request.POST.get('tafsir_author') or "O'zim"
            obj.save(update_fields=['tafsir_text', 'tafsir_author'])
            check_and_award_badges(request.user)
            return redirect('memorize_ayah', surah_id=surah_id, ayah_id=ayah_id)
            
        return redirect('memorize_ayah', surah_id=surah_id, ayah_id=ayah_id)

    context = {
        'surah_id': surah_id, 'ayah_id': ayah_id,
        'text_colored': mark_safe(tajweed_html),
        'transliteration': transliteration,
        'surah_name': ayah_data['surah']['englishName'],
        'surah_arabic': ayah_data['surah']['name'],
        'audio_url': audio_url, 'audio_url_muaiqly': audio_url_muaiqly,
        'obj': obj,
        'prev_ayah': ayah_id - 1 if ayah_id > 1 else None,
        'next_ayah': ayah_id + 1 if ayah_id < ayah_data['surah']['numberOfAyahs'] else None,
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
    check_and_award_badges(request.user)
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
    check_and_award_badges(request.user)
    
    # Memorize qilinganda:
    if obj.is_memorized:
        update_quest_progress(request.user, 'hifz', amount=1)
    
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