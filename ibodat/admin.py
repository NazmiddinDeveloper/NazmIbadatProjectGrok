from django.contrib import admin
from .models import PrayerTime, PrayerLog

@admin.register(PrayerTime)
class PrayerTimeAdmin(admin.ModelAdmin):
    list_display = ['date', 'prayer', 'time']
    list_filter  = ['prayer']

@admin.register(PrayerLog)
class PrayerLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'prayer', 'is_done', 'status', 'done_at']
    list_filter  = ['prayer', 'status', 'is_done']   
