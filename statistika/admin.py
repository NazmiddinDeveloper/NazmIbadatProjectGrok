from django.contrib import admin
from .models import DailyStat

@admin.register(DailyStat)
class DailyStatAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'task_efficiency', 'quran_efficiency', 'overall_efficiency']
    list_filter = ['date']
    search_fields = ['user__username']