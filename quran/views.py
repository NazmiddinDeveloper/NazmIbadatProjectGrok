import requests
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from .models import AyahMemorization
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
def quran_home(request):
    surahs = cache.get('all_surahs')
    if not surahs:
        try:
            r = requests.get('https://api.alquran.cloud/v1/surah', timeout=5)
            surahs = r.json()['data']
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
    cache_key = f'surah_detail_mushaf_v2_{surah_id}'
    cached_data = cache.get(cache_key)

    if not cached_data:
        try:
            r_info = requests.get(f'https://api.alquran.cloud/v1/surah/{surah_id}', timeout=5)
            surah_data = r_info.json()['data']

            words_data = {}
            page = 1
            while True:
                r_words = requests.get(
                    f'https://api.quran.com/api/v4/verses/by_chapter/{surah_id}?words=true&word_fields=text_uthmani,line_number&per_page=50&page={page}',
                    timeout=8
                ).json()
                
                verses = r_words.get('verses', [])
                if not verses:
                    break
                    
                for v in verses:
                    ayah_num = int(v['verse_key'].split(':')[1])
                    lines = {}
                    for w in v['words']:
                        l_num = w['line_number']
                        if l_num not in lines:
                            lines[l_num] = []
                        lines[l_num].append(w.get('text_uthmani', ''))
                    
                    formatted_text = "<br>".join([" ".join(lines[k]) for k in sorted(lines.keys())])
                    words_data[ayah_num] = formatted_text

                pagination = r_words.get('pagination', {})
                if page >= pagination.get('total_pages', 1):
                    break
                page += 1
            
            r_trans = requests.get(f'https://quranenc.com/api/v1/translation/sura/uzbek_mansour/{surah_id}', timeout=5)
            translation_list = r_trans.json().get('result', [])
            translation_data = {int(item['aya']): item['translation'] for item in translation_list}
            
            cached_data = {
                'surah_data': surah_data, 
                'words_data': words_data,
                'translation_data': translation_data
            }
            cache.set(cache_key, cached_data, timeout=86400 * 30)
        except Exception as e:
            print(f"Surah detail xatosi: {e}")
            return redirect('quran_home')
    else:
        surah_data = cached_data['surah_data']
        words_data = cached_data['words_data']
        translation_data = cached_data.get('translation_data', {})

    progress = AyahMemorization.objects.filter(user=request.user, surah_number=surah_id)
    memo_dict = {p.ayah_number: p for p in progress}

    ayahs = []
    for ayah in surah_data['ayahs']:
        num = ayah['numberInSurah']
        p = memo_dict.get(num)

        formatted_html = words_data.get(num, ayah['text'])
        translation_text = translation_data.get(num, "")
        
        ayahs.append({
            'number': num,
            'text_standard': ayah['text'], # <-- Eski versiyadagi oddiy matn
            'text_mushaf': mark_safe(formatted_html), # <-- Mushaf qatorlari
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
    verse_key = f"{surah_id}:{ayah_id}"
    
    try:
        r_ayah = requests.get(f"https://api.quran.com/api/v4/verses/by_key/{verse_key}?fields=page_number", timeout=5)
        page_number = r_ayah.json()['verse']['page_number']
        
        r_page = requests.get(f"https://api.quran.com/api/v4/verses/by_page/{page_number}?words=true&word_fields=text_uthmani,line_number", timeout=8)
        page_verses = r_page.json().get('verses', [])
        
        lines_dict = {}
        for verse in page_verses:
            v_key = verse['verse_key']
            for word in verse['words']:
                l_num = word['line_number']
                if l_num not in lines_dict:
                    lines_dict[l_num] = []
                
                lines_dict[l_num].append({
                    'text': word.get('text_uthmani', ''),
                    'is_target': v_key == verse_key,
                })
        
        mushaf_lines = [lines_dict[k] for k in sorted(lines_dict.keys())]
        
        r_info = requests.get(f'https://api.alquran.cloud/v1/ayah/{verse_key}/en.transliteration', timeout=5)
        ayah_info = r_info.json()['data']
        surah_name = ayah_info['surah']['englishName']
        surah_arabic = ayah_info['surah']['name']
        transliteration = ayah_info['text']
        total_ayahs = ayah_info['surah']['numberOfAyahs']

        # Eski versiyadagi oddiy bitta oyat matnini olish
        r_ayah_std = requests.get(f'https://api.alquran.cloud/v1/ayah/{verse_key}/quran-uthmani', timeout=5)
        ayah_text_standard = r_ayah_std.json()['data']['text']
        
    except Exception as e:
        print(f"Memorize ayah xatosi: {e}")
        return redirect('surah_detail', surah_id=surah_id)

    audio_url = f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{ayah_info['number']}.mp3"
    audio_url_muaiqly = f"https://cdn.islamic.network/quran/audio/128/ar.mahermuaiqly/{ayah_info['number']}.mp3"

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
        'ayah_text_standard': ayah_text_standard, # <-- Oddiy matn
        'mushaf_lines': mushaf_lines,             # <-- Mushaf sahifasi
        'page_number': page_number,
        'transliteration': transliteration,
        'surah_name': surah_name,
        'surah_arabic': surah_arabic,
        'audio_url': audio_url,
        'audio_url_muaiqly': audio_url_muaiqly,
        'obj': obj,
        'prev_ayah': ayah_id - 1 if ayah_id > 1 else None,
        'next_ayah': ayah_id + 1 if ayah_id < total_ayahs else None,
    }
    return render(request, 'quran/memorize.html', context)

# ... (qolgan API funksiyalar o'zgarishsiz qoladi)
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