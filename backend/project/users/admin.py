from django.contrib import admin
from .models import UserProfile, Complaint, Notification

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'latitude', 'longitude')
    search_fields = ('user__username',)
    list_filter = ('created_at',)

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'complaint_type', 'status', 'created_at')
    list_filter = ('complaint_type', 'status', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'ai_classification')
    list_editable = ('status',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'description', 'complaint_type')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Status & Classification', {
            'fields': ('status', 'ai_classification')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    readonly_fields = ('created_at',)
