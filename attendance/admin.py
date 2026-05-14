from django.contrib import admin
from .models import ClockIssue, ClockRecord, Leave
from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'created_by', 'send_time', 'send_to')
    list_filter = ('created_by', 'send_time')
    search_fields = ('title', 'content')

@admin.register(ClockIssue)
class ClockIssueAdmin(admin.ModelAdmin):
    list_display = ('id', 'address', 'start_time', 'end_time', 'issued_by')
    list_filter = ('issued_by',)

@admin.register(ClockRecord)
class ClockRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'issue', 'clock_time', 'status')
    list_filter = ('status',)

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'type', 'status', 'apply_time')
    list_filter = ('type', 'status')