# gamification/services.py
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from .models import DailyQuest, Badge, UserBadge
from ibodat.models import PrayerLog
from dashboard.models import Task
from quran.models import AyahMemorization


def check_and_award_badges(user):
    """Badge berish logikasi (oldingi kabi qoldi)"""
    awarded = []

    if user.streak >= 7 and not UserBadge.objects.filter(user=user, badge__condition='7_day_streak').exists():
        badge = Badge.objects.get(condition='7_day_streak')
        UserBadge.objects.create(user=user, badge=badge)
        user.xp += badge.xp_bonus
        awarded.append(badge.name)

    if user.streak >= 30 and not UserBadge.objects.filter(user=user, badge__condition='30_day_streak').exists():
        badge = Badge.objects.get(condition='30_day_streak')
        UserBadge.objects.create(user=user, badge=badge)
        user.xp += badge.xp_bonus
        awarded.append(badge.name)

    perfect_days = PrayerLog.objects.filter(
        user=user, is_done=True, status='on_time'
    ).values('date').annotate(count=Count('prayer')).filter(count=5).count()

    if perfect_days >= 7 and not UserBadge.objects.filter(user=user, badge__condition='perfect_7_days').exists():
        badge = Badge.objects.get(condition='perfect_7_days')
        UserBadge.objects.create(user=user, badge=badge)
        user.xp += badge.xp_bonus
        awarded.append(badge.name)

    memorized_count = AyahMemorization.objects.filter(user=user, is_memorized=True).count()
    if memorized_count >= 100 and not UserBadge.objects.filter(user=user, badge__condition='100_ayah').exists():
        badge = Badge.objects.get(condition='100_ayah')
        UserBadge.objects.create(user=user, badge=badge)
        user.xp += badge.xp_bonus
        awarded.append(badge.name)

    if awarded:
        user.level = (user.xp // 500) + 1
        user.save(update_fields=['xp', 'level'])

    return awarded


def generate_daily_quests(user):
    """
    Hybrid Daily Quest yaratadi.
    Oxirgi 7 kunlik faollikka qarab avtomatik moslashtiradi.
    """
    today = timezone.localdate()

    # Bugun allaqachon quest yaratilganmi?
    if DailyQuest.objects.filter(user=user, date=today).exists():
        return

    last_7_days = today - timedelta(days=7)

    # === Statistikalar ===
    prayers_done = PrayerLog.objects.filter(
        user=user, date__gte=last_7_days, is_done=True
    ).count()

    tasks_done = Task.objects.filter(
        user=user, due_date__gte=last_7_days, is_completed=True
    ).count()

    hifz_done = AyahMemorization.objects.filter(
        user=user, last_practiced__date__gte=last_7_days
    ).count()

    avg_prayer = prayers_done / 7
    avg_task = tasks_done / 7

    quests_to_create = []

    # === HOLATNI BAHOLASH ===
    if avg_prayer < 3 or avg_task < 1:
        # Pastga tushayotgan — xavotir beruvchi + oson questlar
        quests_to_create = [
            {
                'title': 'Bugun 3 ta namozni vaqtida o‘qing',
                'description': 'Siz so‘nggi kunlarda biroz zaifroq bo‘lib qoldingiz. Kichik qadamdan boshlaymiz.',
                'target_type': 'prayer',
                'target_value': 3,
                'xp_reward': 80,
                'motivational_message': 'Har bir namoz — bu sizning o‘zingiz bilan bo‘lgan suhbatingiz. Bugun o‘zingizga vaqt ajrating.'
            },
            {
                'title': 'Faqat 1 ta vazifani bajaring',
                'description': 'Katta yuklamang. Bitta kichik vazifani bajarish ham katta yutuq.',
                'target_type': 'task',
                'target_value': 1,
                'xp_reward': 60,
                'motivational_message': 'Kichik g‘alabalar katta o‘zgarishlarga olib keladi.'
            }
        ]
    else:
        # Yaxshilanayotgan yoki barqaror — hamd va shukr + biroz qiyinroq
        quests_to_create = [
            {
                'title': '5 ta namozni vaqtida o‘qing',
                'description': 'Siz yaxshi natija ko‘rsatmoqdasiz. Davom eting!',
                'target_type': 'prayer',
                'target_value': 5,
                'xp_reward': 120,
                'motivational_message': 'Alloh sizning sa’y-harakatlaringizni qabul qilsin. Ajoyib ish qilyapsiz!'
            },
            {
                'title': '3 ta vazifani bajaring',
                'description': 'Sizning intizomingiz o‘smoqda. Bugun ham shunday davom eting.',
                'target_type': 'task',
                'target_value': 3,
                'xp_reward': 100,
                'motivational_message': 'Har bir bajarilgan vazifa — bu sizning kelajagingizga qo‘yilgan g‘isht.'
            },
            {
                'title': 'Kamida 5 ta oyat yodlang yoki takrorlang',
                'description': 'Qur’on bilan bog‘lanishni davom ettiring.',
                'target_type': 'hifz',
                'target_value': 5,
                'xp_reward': 90,
                'motivational_message': 'Qur’on — bu nur. Uni har kuni o‘zingizga yaqin tuting.'
            }
        ]

    # Questlarni yaratamiz
    for q in quests_to_create:
        DailyQuest.objects.create(
            user=user,
            date=today,
            title=q['title'],
            description=q['description'],
            target_type=q['target_type'],
            target_value=q['target_value'],
            xp_reward=q['xp_reward'],
            motivational_message=q['motivational_message'],
            is_auto_generated=True
        )

def update_quest_progress(user, target_type, amount=1):
    """
    Foydalanuvchi biror harakat qilganda (namoz, vazifa, hifz)
    tegishli questning progressini yangilaydi.
    """
    today = timezone.localdate()
    
    quests = DailyQuest.objects.filter(
        user=user,
        date=today,
        target_type=target_type,
        status='pending'
    )

    for quest in quests:
        quest.current_progress += amount
        
        # Agar bajarilgan bo‘lsa
        if quest.current_progress >= quest.target_value:
            quest.current_progress = quest.target_value
            quest.status = 'completed'
            
            # XP beramiz
            user.xp += quest.xp_reward
            user.level = (user.xp // 500) + 1
            user.save(update_fields=['xp', 'level'])
            
            # Badge tekshiramiz
            check_and_award_badges(user)
        
        quest.save()