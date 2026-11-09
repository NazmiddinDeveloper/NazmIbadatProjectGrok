import re
import requests
import json
from datetime import timedelta
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import AyahMemorization


@login_required
def hifz_test_view(request):
    today = timezone.localdate()

    # Faqat foydalanuvchining yodlangan oyatlari
    memorized_ayahs = AyahMemorization.objects.filter(
        user=request.user,
        is_memorized=True
    ).order_by('surah_number', 'ayah_number')

    cached_ayahs = []

    for memo in memorized_ayahs:
        verse_key = f"{memo.surah_number}:{memo.ayah_number}"

        # 1. Memorize sahifasida saqlangan cache
        cached_info = cache.get(f"q_ayah_info_v8_{verse_key}")

        text_html = ""
        page_number = None
        surah_name = f"Sura {memo.surah_number}"

        if cached_info:
            text_html = (
                cached_info.get('ayah_text_tajweed')
                or cached_info.get('ayah_text_standard')
                or ""
            )
            page_number = cached_info.get('page_number')
            surah_name = cached_info.get('surah_name', surah_name)

        # 2. Agar memorize cache bo'lmasa, Qur'on surah sahifasi cache'idan olamiz
        if not text_html:
            surah_cache = cache.get(
                f"surah_detail_tajweed_v8_{memo.surah_number}"
            )

            if surah_cache:
                surah_data = surah_cache.get('surah_data') or {}
                tajweed_map = surah_cache.get('tajweed_map') or {}

                for ayah in surah_data.get('ayahs', []):
                    if int(ayah.get('numberInSurah', 0)) == memo.ayah_number:
                        text_html = (
                            tajweed_map.get(memo.ayah_number)
                            or ayah.get('text', '')
                        )
                        surah_name = surah_data.get(
                            'englishName', surah_name
                        )
                        break

        # Cache'da matn bo'lmasa, testga qo'shmaymiz
        if not text_html:
            continue

        cached_ayahs.append({
            'id': memo.id,
            'surah': memo.surah_number,
            'ayah': memo.ayah_number,
            'page': page_number,
            'surah_name': surah_name,
            'text': text_html,
        })

    # Xatolar ro'yxati
    mistakes = AyahMemorization.objects.filter(
        user=request.user,
        failed_attempts__gt=0
    ).order_by('-failed_attempts')

    context = {
        'cached_ayahs': cached_ayahs,
        'mistakes': mistakes,
        'cached_ayah_count': len(cached_ayahs),
    }

    return render(request, 'quran/hifz_test.html', context)

@login_required
@require_POST
def submit_hifz_review(request):
    try:
        data = json.loads(request.body)
        ayah_id = data.get('ayah_id')
        status = data.get('status') # 'success' yoki 'failed'
        
        memo = AyahMemorization.objects.get(id=ayah_id, user=request.user)
        
        # SuperMemo-2 (SM-2) asosidagi algoritm
        if status == 'success':
            if memo.interval == 0:
                memo.interval = 1
            elif memo.interval == 1:
                memo.interval = 6
            else:
                memo.interval = int(memo.interval * memo.ease_factor)
            
            # Osonlik darajasini biroz oshiramiz
            memo.ease_factor = round(memo.ease_factor + 0.1, 2)
        else:
            # Agar xato qilsa, interval nollanadi va yana tez-tez so'raladigan bo'ladi
            memo.interval = 0
            memo.ease_factor = max(1.3, round(memo.ease_factor - 0.2, 2))
            memo.failed_attempts += 1
            
        memo.next_review_date = timezone.localdate() + timedelta(days=memo.interval)
        memo.save()
        
        return JsonResponse({'status': 'ok', 'next_review': memo.next_review_date})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def mark_mistake(request):
    data = json.loads(request.body)
    surah = data.get('surah')
    ayah = data.get('ayah')
    
    memo, created = AyahMemorization.objects.get_or_create(
        user=request.user, 
        surah_number=surah, 
        ayah_number=ayah
    )
    memo.failed_attempts += 1
    memo.save()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def remove_mistake(request):
    data = json.loads(request.body)
    surah = data.get('surah')
    ayah = data.get('ayah')
    
    try:
        memo = AyahMemorization.objects.get(user=request.user, surah_number=surah, ayah_number=ayah)
        memo.failed_attempts = 0
        memo.save()
    except:
        pass
    return JsonResponse({'status': 'ok'})

# Alquran.cloud ning [h:1[ٱ] formatidagi tajvid kodlarini Quran.com ning <tajweed class="..."> formatiga 100% o'giruvchi lug'at
ALQURAN_TAJWEED_MAP = {
    'h': 'ham_wasl',
    's': 'slnt',
    'l': 'laam_shamsiyah',
    'n': 'madda_normal',
    'p': 'madda_permissible',
    'm': 'madda_necessary',
    'o': 'madda_obligatory',
    'q': 'qalaqah',
    'g': 'ghunnah',
    'f': 'ikhafa',
    'c': 'ikhafa_shafawi',
    'a': 'idgham_ghunnah',
    'u': 'idgham_wo_ghunnah',
    'w': 'idgham_shafawi',
    'd': 'idgham_mutajanisayn',
    'b': 'idgham_mutaqaribayn',
    'i': 'iqlab',
}


def convert_alquran_tajweed_to_html(raw_text: str) -> str:
    """Alquran.cloud [q:12[قْ] formatini Quran.com <tajweed class="qalaqah">قْ</tajweed> formatiga aylantiradi."""
    if not raw_text:
        return ""
    pattern = re.compile(r'\[([a-zA-Z]+)(?::\d+)?\[([^\]]+)\]')
    return pattern.sub(
        lambda m: f'<tajweed class="{ALQURAN_TAJWEED_MAP.get(m.group(1), m.group(1))}">{m.group(2)}</tajweed>',
        raw_text
    )


def clean_tajweed_end_marker(html_text: str) -> str:
    """Quran.com uthmani_tajweed oxiridagi <span class=end>١</span> raqamini olib tashlaydi."""
    if not html_text:
        return ""
    return re.sub(r'<span\s+class=["\']?end["\']?[^>]*>.*?</span>', '', html_text).strip()


@login_required
def quran_home(request):
    surahs = cache.get('all_surahs')
    if not surahs:
        try:
            r = requests.get('https://api.alquran.cloud/v1/surah', timeout=8)
            surahs = r.json()['data']
            cache.set('all_surahs', surahs, timeout=86400 * 30)
        except Exception as e:
            print(f"Quran home xatosi: {e}")
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
    cache_key = f'surah_detail_tajweed_v8_{surah_id}'
    cached_data = cache.get(cache_key)

    if not cached_data:
        surah_data = None
        translation_data = {}
        tajweed_map = {}

        # 1. Alquran.cloud orqali Sura + O'zbekcha tarjima + Tajvid nusxasini BITTA so'rovda olamiz!
        try:
            r_info = requests.get(
                f'https://api.alquran.cloud/v1/surah/{surah_id}/editions/quran-uthmani,uz.sodik,quran-tajweed',
                timeout=12
            )
            ed_data = r_info.json().get('data', [])
            if len(ed_data) >= 1:
                surah_data = ed_data[0]
            if len(ed_data) >= 2:
                for item in ed_data[1].get('ayahs', []):
                    translation_data[int(item['numberInSurah'])] = item['text']
            if len(ed_data) >= 3:
                for item in ed_data[2].get('ayahs', []):
                    num = int(item['numberInSurah'])
                    tajweed_map[num] = convert_alquran_tajweed_to_html(item['text'])
        except Exception as e:
            print(f"Alquran multi-edition xatosi: {e}")

        if not surah_data:
            try:
                r_info = requests.get(f'https://api.alquran.cloud/v1/surah/{surah_id}', timeout=8)
                surah_data = r_info.json()['data']
            except Exception as e:
                print(f"Surah detail xatosi: {e}")
                return redirect('quran_home')

        # 2. Quran.com rasmiy uthmani_tajweed API (Agar ulansa, ustidan yanada boyitadi)
        qdc_urls = [
            f"https://api.qurancdn.com/api/qdc/quran/verses/uthmani_tajweed?chapter_number={surah_id}",
            f"https://api.quran.com/api/v4/quran/verses/uthmani_tajweed?chapter_number={surah_id}",
        ]
        for url in qdc_urls:
            try:
                r_tj = requests.get(url, timeout=6)
                if r_tj.status_code == 200:
                    verses = r_tj.json().get('verses', [])
                    if verses:
                        for v in verses:
                            v_num = int(v['verse_key'].split(':')[1])
                            tajweed_map[v_num] = clean_tajweed_end_marker(v.get('text_uthmani_tajweed', ''))
                        break
            except Exception as e:
                print(f"QuranCDN Tajweed ogohlantirishi: {e}")

        cached_data = {
            'surah_data': surah_data,
            'translation_data': translation_data,
            'tajweed_map': tajweed_map,
        }
        cache.set(cache_key, cached_data, timeout=86400 * 30)
    else:
        surah_data = cached_data['surah_data']
        translation_data = cached_data.get('translation_data', {})
        tajweed_map = cached_data.get('tajweed_map', {})

    progress = AyahMemorization.objects.filter(user=request.user, surah_number=surah_id)
    memo_dict = {p.ayah_number: p for p in progress}

    ayahs = []
    for ayah in surah_data['ayahs']:
        num = ayah['numberInSurah']
        p = memo_dict.get(num)

        colored_html = tajweed_map.get(num) or ayah['text']

        ayahs.append({
            'number': num,
            'text_colored': mark_safe(colored_html),
            'translation': translation_data.get(num, ""),
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

    page_number = 1
    global_num = 1
    ayah_text_standard = ""
    ayah_text_tajweed = ""
    surah_name = f"Sura {surah_id}"
    surah_arabic = ""
    transliteration = ""
    total_ayahs = 286
    mushaf_lines = []

    # 1-QADAM: Oyatning sahifa raqami, transkripsiyasi va Tajvidli matnini olamiz
    info_cache_key = f"q_ayah_info_v8_{verse_key}"
    cached_info = cache.get(info_cache_key)
    if not cached_info:
        try:
            r_info = requests.get(
                f'https://api.alquran.cloud/v1/ayah/{verse_key}/editions/quran-uthmani,en.transliteration,quran-tajweed',
                timeout=8
            )
            ed_list = r_info.json().get('data', [])
            if len(ed_list) >= 1:
                ar_info = ed_list[0]
                raw_tj = ed_list[2].get('text', '') if len(ed_list) >= 3 else ''
                cached_info = {
                    'ayah_text_standard': ar_info.get('text', ''),
                    'ayah_text_tajweed': convert_alquran_tajweed_to_html(raw_tj) or ar_info.get('text', ''),
                    'page_number': ar_info.get('page', 1),
                    'global_num': ar_info.get('number', 1),
                    'surah_name': ar_info['surah']['englishName'],
                    'surah_arabic': ar_info['surah']['name'],
                    'total_ayahs': ar_info['surah']['numberOfAyahs'],
                    'transliteration': ed_list[1].get('text', '') if len(ed_list) >= 2 else '',
                }
                cache.set(info_cache_key, cached_info, timeout=86400 * 30)
        except Exception as e:
            print(f"Ayah info ogohlantirishi: {e}")

    if cached_info:
        ayah_text_standard = cached_info['ayah_text_standard']
        ayah_text_tajweed = cached_info.get('ayah_text_tajweed') or ayah_text_standard
        page_number = cached_info['page_number']
        global_num = cached_info['global_num']
        surah_name = cached_info['surah_name']
        surah_arabic = cached_info['surah_arabic']
        total_ayahs = cached_info['total_ayahs']
        transliteration = cached_info['transliteration']

    # 2-QADAM: QuranCDN dan rasmiy uthmani_tajweed va code_v2 Mushaf qatorlarini olish
    page_cache_key = f"q_mushaf_page_v8_{page_number}"
    page_verses = cache.get(page_cache_key)

    if not page_verses:
        mushaf_urls = [
            f"https://api.qurancdn.com/api/qdc/verses/by_page/{page_number}?words=true&word_fields=code_v2,text_uthmani,line_number,page_number&mushaf=1",
            f"https://api.quran.com/api/v4/verses/by_page/{page_number}?mushaf=1&words=true&word_fields=code_v2,text_uthmani,line_number,page_number",
        ]
        for url in mushaf_urls:
            try:
                r_page = requests.get(url, timeout=6)
                if r_page.status_code == 200:
                    page_verses = r_page.json().get('verses', [])
                    if page_verses:
                        cache.set(page_cache_key, page_verses, timeout=86400 * 30)
                        break
            except Exception as e:
                print(f"Mushaf URL ({url}) ogohlantirishi: {e}")

    if page_verses:
        lines_dict = {}
        for verse in page_verses:
            v_key = verse.get('verse_key')
            for word in verse.get('words', []):
                l_num = word.get('line_number')
                if l_num not in lines_dict:
                    lines_dict[l_num] = []

                is_target = (v_key == verse_key)
                lines_dict[l_num].append({
                    'text': word.get('code_v2') or word.get('text_uthmani', ''),
                    'display_text': word.get('text_uthmani', ''),
                    'is_target': is_target,
                })

        mushaf_lines = [lines_dict[k] for k in sorted(lines_dict.keys())]

    audio_url = f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{global_num}.mp3"
    audio_url_muaiqly = f"https://cdn.islamic.network/quran/audio/128/ar.mahermuaiqly/{global_num}.mp3"
    audio_url_husary = f"https://cdn.islamic.network/quran/audio/128/ar.husary/{global_num}.mp3"
    audio_url_minshawi = f"https://cdn.islamic.network/quran/audio/128/ar.minshawi/{global_num}.mp3"
    audio_url_abdulbasit = f"https://cdn.islamic.network/quran/audio/192/ar.abdulbasitmurattal/{global_num}.mp3"

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
        elif action == 'save_tafsir':
            obj.tafsir_text = request.POST.get('tafsir_text')
            obj.tafsir_author = request.POST.get('tafsir_author') or "O'zim"
            obj.save(update_fields=['tafsir_text', 'tafsir_author'])

        return redirect('memorize_ayah', surah_id=surah_id, ayah_id=ayah_id)

    context = {
        'surah_id': surah_id,
        'ayah_id': ayah_id,
        'verse_key': verse_key,
        'mushaf_lines': mushaf_lines,
        'ayah_text_standard': mark_safe(ayah_text_tajweed),
        'page_number': page_number,
        'transliteration': transliteration,
        'surah_name': surah_name,
        'surah_arabic': surah_arabic,
        'audio_url': audio_url,
        'audio_url_muaiqly': audio_url_muaiqly,
        'audio_url_husary': audio_url_husary,
        'audio_url_minshawi': audio_url_minshawi,
        'audio_url_abdulbasit': audio_url_abdulbasit,
        'obj': obj,
        'prev_ayah': ayah_id - 1 if ayah_id > 1 else None,
        'next_ayah': ayah_id + 1 if ayah_id < total_ayahs else None,
    }
    return render(request, 'quran/memorize.html', context)


@login_required
@require_POST
def api_repeat(request, surah_id, ayah_id):
    obj, _ = AyahMemorization.objects.get_or_create(
        user=request.user, surah_number=surah_id, ayah_number=ayah_id
    )
    if request.GET.get('reset') == '1':
        obj.repeats = 0
    else:
        obj.repeats += 1
    obj.save(update_fields=['repeats', 'last_practiced'])
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
        obj.save(update_fields=['is_memorized', 'repeats', 'last_practiced'])
    else:
        obj.save(update_fields=['is_memorized', 'last_practiced'])

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