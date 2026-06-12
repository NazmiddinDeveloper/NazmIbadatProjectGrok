from django.core.management.base import BaseCommand
from gamification.models import Badge

class Command(BaseCommand):
    help = 'Barcha default badge\'larni yaratadi'

    def handle(self, *args, **options):
        badges = [
            {
                "name": "7 Kunlik Sadoqat",
                "description": "7 kun uzluksiz streak",
                "icon": "🔥",
                "condition": "7_day_streak",
                "xp_bonus": 150
            },
            {
                "name": "Temir Inson",
                "description": "30 kun uzluksiz streak",
                "icon": "⚡",
                "condition": "30_day_streak",
                "xp_bonus": 500
            },
            {
                "name": "Namoz Ustasi",
                "description": "7 kun ketma-ket 5 ta namoz vaqtida",
                "icon": "🕌",
                "condition": "perfect_7_days",
                "xp_bonus": 300
            },
            {
                "name": "Yuz Oyat",
                "description": "100 ta oyat yod olding",
                "icon": "📖",
                "condition": "100_ayah",
                "xp_bonus": 400
            },
        ]

        created_count = 0
        for data in badges:
            badge, created = Badge.objects.get_or_create(
                condition=data['condition'],
                defaults=data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Yaratildi: {badge.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ Allaqachon mavjud: {badge.name}'))

        self.stdout.write(self.style.SUCCESS(f'\nJami {created_count} ta badge yaratildi!'))