import requests
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from .models import AyahMemorization
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import re

# ==================== YORDAMCHI FUNKSIYA ====================
def remove_inline_styles(html):
    """Inline style atributlarini HTML'dan olib tashlash"""
    return re.sub(r' style="[^"]*"', '', html)

def get_tajweed_ayah(surah: int, ayah: int):
    verse_key = f"{surah}:{ayah}"
    url = f"https://api.quran.com/api/v4/quran/verses/uthmani_tajweed?verse_key={verse_key}"
    
    try:
        response = requests.get(url, timeout=6)
        data = response.json()
        if data.get("verses"):
            return data["verses"][0].get("text_uthmani_tajweed", "")
    except Exception as e:
        print(f"Tajweed API xatosi: {e}")
    return None


@login_required
def quran_home(request):
    # Suralar ro'yxatini keshdan qidiramiz
    surahs = cache.get('all_surahs')
    
    if not surahs:
        try:
            r = requests.get('https://api.alquran.cloud/v1/surah', timeout=5)
            surahs = r.json()['data']
            # Suralar ro'yxatini 30 kunga keshga saqlaymiz
            cache.set('all_surahs', surahs, timeout=86400 * 30)
        except:
            surahs = []

    memorized_count = AyahMemorization.objects.filter(
        user=request.user, is_memorized=True
    ).count()
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
    cache_key = f'surah_detail_data_v2_{surah_id}'   # ← v2 qo'shildi
    cached_data = cache.get(cache_key)

    if not cached_data:
        try:
            # 1. Sura haqida umumiy ma'lumot va arabcha matn
            r_info = requests.get(f'https://api.alquran.cloud/v1/surah/{surah_id}', timeout=5)
            surah_data = r_info.json()['data']

            # 2. Barcha oyatlar uchun Tajweed ma'lumotini olish
            r_tajweed = requests.get(
                f'https://api.quran.com/api/v4/quran/verses/uthmani_tajweed?chapter_number={surah_id}',
                timeout=8
            )
            tajweed_data = r_tajweed.json().get('verses', [])
            
            # 3. O'zbekcha tarjimani olish (Alauddin Mansur - quranenc.com)
            r_trans = requests.get(f'https://quranenc.com/api/v1/translation/sura/uzbek_mansour/{surah_id}', timeout=5)
            translation_list = r_trans.json().get('result', [])
            # Aya raqami bo'yicha dict qilamiz — tartib mos kelmay qolsa ham xato bermaydi
            translation_data = {int(item['aya']): item['translation'] for item in translation_list}
            
            cached_data = {
                'surah_data': surah_data, 
                'tajweed_data': tajweed_data,
                'translation_data': translation_data
            }
            # Sura ichidagi ma'lumotlarni 30 kunga keshlaymiz
            cache.set(cache_key, cached_data, timeout=86400 * 30)
        except Exception as e:
            print(f"Surah detail xatosi: {e}")
            return redirect('quran_home')
    else:
        surah_data = cached_data['surah_data']
        tajweed_data = cached_data['tajweed_data']
        translation_data = cached_data.get('translation_data', {})   # ← list emas, dict

    progress = AyahMemorization.objects.filter(user=request.user, surah_number=surah_id)
    memo_dict = {p.ayah_number: p for p in progress}

    ayahs = []
    for i, ayah in enumerate(surah_data['ayahs']):
        num = ayah['numberInSurah']
        p = memo_dict.get(num)

        tajweed_html = tajweed_data[i]['text_uthmani_tajweed'] if i < len(tajweed_data) else ayah['text']
        tajweed_html = remove_inline_styles(tajweed_html)  # ← Inline style'larni olib tashlash
        
        translation_text = translation_data.get(num, "")   # ← shu qatorni o'zgartiring
        ayahs.append({
            'number': num,
            'text_colored': mark_safe(tajweed_html),
            'translation': translation_text,
            'is_memorized': p.is_memorized if p else False,
            'repeats': p.repeats if p else 0,
        })
    
    return render(request, 'quran/surah_detail.html', {
        'surah': surah_data,
        'ayahs': ayahs
    })

@login_required
def memorize_ayah(request, surah_id, ayah_id):
    try:
        r = requests.get(f'https://api.alquran.cloud/v1/ayah/{surah_id}:{ayah_id}/quran-uthmani', timeout=5)
        ayah_data = r.json()['data']

        # Tajweed matnini olish
        tajweed_html = get_tajweed_ayah(surah_id, ayah_id)
        if not tajweed_html:
            tajweed_html = ayah_data['text']  # Agar Tajweed bo'lmasa oddiy matn
        
        tajweed_html = remove_inline_styles(tajweed_html)  # ← Inline style'larni olib tashlash

        # Transkripsiya
        r_trans = requests.get(f'https://api.alquran.cloud/v1/ayah/{surah_id}:{ayah_id}/en.transliteration', timeout=5)
        transliteration = r_trans.json()['data']['text']
    except Exception as e:
        print(f"Memorize ayah xatosi: {e}")
        return redirect('surah_detail', surah_id=surah_id)

    audio_url = f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{ayah_data['number']}.mp3"
    audio_url_muaiqly = f"https://cdn.islamic.network/quran/audio/128/ar.mahermuaiqly/{ayah_data['number']}.mp3"

    obj, _ = AyahMemorization.objects.get_or_create(
        user=request.user,
        surah_number=surah_id,
        ayah_number=ayah_id
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if 'custom_audio' in request.FILES:
            obj.custom_audio = request.FILES['custom_audio']
            obj.custom_audio_title = request.POST.get('audio_title', 'Mening audim')
            obj.save()

        elif action == 'repeat':
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

        elif action == 'delete_image':
            if obj.mushaf_image:
                obj.mushaf_image.delete()
            return redirect('memorize_ayah', surah_id=surah_id, ayah_id=ayah_id)

        elif action == 'save_tafsir':
            obj.tafsir_text = request.POST.get('tafsir_text')
            obj.tafsir_author = request.POST.get('tafsir_author') or "O'zim"
            obj.save(update_fields=['tafsir_text', 'tafsir_author'])
            return redirect('memorize_ayah', surah_id=surah_id, ayah_id=ayah_id)

        return redirect('memorize_ayah', surah_id=surah_id, ayah_id=ayah_id)

    context = {
        'surah_id': surah_id,
        'ayah_id': ayah_id,
        'text_colored': mark_safe(tajweed_html),           # ← Asosiy matn
        'tajweed_text': mark_safe(tajweed_html),           # ← Template uchun qo‘shimcha
        'transliteration': transliteration,
        'surah_name': ayah_data['surah']['englishName'],
        'surah_arabic': ayah_data['surah']['name'],
        'audio_url': audio_url,
        'audio_url_muaiqly': audio_url_muaiqly,
        'obj': obj,
        'prev_ayah': ayah_id - 1 if ayah_id > 1 else None,
        'next_ayah': ayah_id + 1 if ayah_id < ayah_data['surah']['numberOfAyahs'] else None,
    }
    return render(request, 'quran/memorize.html', context)


# ==================== AJAX FUNKSIYALAR ====================

@login_required
@require_POST
def api_repeat(request, surah_id, ayah_id):
    obj, _ = AyahMemorization.objects.get_or_create(
        user=request.user, surah_number=surah_id, ayah_number=ayah_id
    )
    obj.repeats += 1
    obj.save(update_fields=['repeats'])
    return JsonResponse({'repeats': obj.repeats, 'status': 'ok'})


@login_required
@require_POST
def api_memorize(request, surah_id, ayah_id):
    obj, _ = AyahMemorization.objects.get_or_create(
        user=request.user, surah_number=surah_id, ayah_number=ayah_id
    )
    obj.is_memorized = not obj.is_memorized
    if obj.is_memorized:
        obj.repeats += 1
        obj.save(update_fields=['is_memorized', 'repeats'])
    else:
        obj.save(update_fields=['is_memorized'])

    return JsonResponse({
        'is_memorized': obj.is_memorized,
        'repeats': obj.repeats,
        'status': 'ok'
    })


@login_required
@require_POST
def api_upload_image(request, surah_id, ayah_id):
    if 'image' not in request.FILES:
        return JsonResponse({'status': 'error', 'msg': 'Rasm yo\'q'}, status=400)

    obj, _ = AyahMemorization.objects.get_or_create(
        user=request.user, surah_number=surah_id, ayah_number=ayah_id
    )
    obj.mushaf_image = request.FILES['image']
    obj.save(update_fields=['mushaf_image'])
    return JsonResponse({'status': 'ok', 'image_url': obj.mushaf_image.url})
