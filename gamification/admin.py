from django.contrib import admin
from .models import Badge, UserBadge

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'condition', 'xp_bonus', 'icon']   # created_at ni olib tashladik
    search_fields = ['name', 'description']
    list_filter = ['condition']


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'earned_at']
    list_filter = ['badge']
    search_fields = ['user__username']
    date_hierarchy = 'earned_at'