"""Django admin customization for notification logs."""

from django.contrib import admin
from django.utils.html import format_html

from apps.notifications.models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Admin interface for monitoring system notifications and email delivery."""

    list_display = (
        'user_email',
        'event_type_colored',
        'channel_icon',
        'status_colored',
        'created_at',
        'sent_at',
    )
    list_filter = (
        'event_type',
        'channel',
        'status',
        'created_at',
        'sent_at',
    )
    search_fields = (
        'user__email',
        'user__username',
        'event_type',
        'subject',
    )
    readonly_fields = (
        'id',
        'user',
        'event_type',
        'channel',
        'status',
        'subject',
        'message',
        'metadata_display',
        'error_message',
        'created_at',
        'sent_at',
    )
    fieldsets = (
        ('Recipient & Event', {
            'fields': ('id', 'user', 'event_type'),
        }),
        ('Content', {
            'fields': ('subject', 'message'),
        }),
        ('Delivery', {
            'fields': ('channel', 'status', 'error_message'),
        }),
        ('Metadata', {
            'fields': ('metadata_display',),
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'sent_at'),
        }),
    )
    date_hierarchy = 'created_at'
    actions = ['mark_as_sent', 'mark_as_failed']

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User'

    def event_type_colored(self, obj):
        """Display event type with color coding."""
        color_map = {
            'EMAIL_VERIFICATION': '#007bff',
            'LOGIN_NEW_IP': '#fd7e14',
            'TOKEN_GENERATED': '#28a745',
            'TOKEN_REGENERATED': '#17a2b8',
            'TOKEN_EXPIRING': '#ffc107',
            'SECURITY_PHOTO_REJECTION': '#dc3545',
        }
        color = color_map.get(obj.event_type, '#6c757d')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_event_type_display(),
        )
    event_type_colored.short_description = 'Event Type'

    def channel_icon(self, obj):
        """Display channel as icon with label."""
        icons = {
            'EMAIL': '<i class="fas fa-envelope"></i> Email',
            'SYSTEM': '<i class="fas fa-desktop"></i> System',
            'BOTH': '<i class="fas fa-bell"></i> Both',
        }
        return format_html(icons.get(obj.channel, obj.channel))
    channel_icon.short_description = 'Channel'

    def status_colored(self, obj):
        """Display status with color coding."""
        color_map = {
            'SENT': '#28a745',
            'QUEUED': '#ffc107',
            'FAILED': '#dc3545',
        }
        color = color_map.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_colored.short_description = 'Status'

    def metadata_display(self, obj):
        """Display metadata as a formatted text block."""
        import json
        if obj.metadata:
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 3px;">{}</pre>',
                             json.dumps(obj.metadata, indent=2))
        return 'No metadata'
    metadata_display.short_description = 'Metadata (Biometric Data Scrubbed)'

    @admin.action(description='Mark selected as SENT')
    def mark_as_sent(self, request, queryset):
        """Manually mark notifications as sent (for admin override)."""
        from django.contrib import messages
        from django.utils import timezone

        updated = 0
        for notif in queryset:
            if notif.status != 'SENT':
                notif.status = 'SENT'
                notif.sent_at = timezone.now()
                notif.save(update_fields=['status', 'sent_at'])
                updated += 1
        self.message_user(request, f'{updated} notification(s) marked as sent.', messages.SUCCESS)

    @admin.action(description='Mark selected as FAILED')
    def mark_as_failed(self, request, queryset):
        """Manually mark notifications as failed for retry."""
        from django.contrib import messages

        updated = queryset.exclude(status='FAILED').update(status='FAILED')
        self.message_user(request, f'{updated} notification(s) marked as failed.', messages.WARNING)

    def has_add_permission(self, request):
        """Prevent manual creation of notification records."""
        return False
