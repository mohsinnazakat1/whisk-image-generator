from django.contrib import admin
from .models import WhiskSettings, BulkImageRequest, ImagePrompt

@admin.register(WhiskSettings)
class WhiskSettingsAdmin(admin.ModelAdmin):
    list_display = ('auth_token', 'project_id', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

    def has_add_permission(self, request):
        # Only allow one instance
        return not WhiskSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the only instance
        return False
