from django.contrib import admin
from .models import SmokeData

@admin.register(SmokeData)
class SmokeDataAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'smoke_level', 'status')
    list_filter = ('status', 'timestamp')
    search_fields = ('smoke_level',)
    readonly_fields = ('timestamp',)
