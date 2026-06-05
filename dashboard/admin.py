from django.contrib import admin
from .models import Task, Shift

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display  = ['title', 'user', 'category', 'priority', 'is_completed', 'due_date']
    list_filter   = ['category', 'priority', 'is_completed']
    search_fields = ['title']

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'shift_type']
    list_filter  = ['shift_type']