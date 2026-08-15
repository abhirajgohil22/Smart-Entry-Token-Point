"""Django admin customization for security photos and audit trails."""

from django.contrib import admin, messages
from django.utils import timezone
from django.urls import reverse
from django.utils.html import format_html

from apps.security_photos.models import SecurityPhoto, ProfilePhoto


@admin.register(SecurityPhoto)
class SecurityPhotoAdmin(admin.ModelAdmin):
    """Admin interface for monitoring security photo events with audit trail."""

    list_display = (
        'request_id_link',
        'user',
        'event_type',
        'captured_at',
        'verification_status_colored',
        'face_recognition_status',
        'ip_address',
        'face_confidence',
    )
    list_filter = (
        'event_type',
        'verification_status',
        'face_recognition_status',
        'captured_at',
    )
    search_fields = (
        'user__email',
        'user__username',
        'user__first_name',
        'user__last_name',
        'request_id',
        'nonce',
        'ip_address',
    )
    readonly_fields = (
        'id',
        'user',
        'event_type',
        'image',
        'request_id',
        'nonce',
        'captured_at',
        'face_recognition_status',
        'face_confidence',
        'ip_address',
        'user_agent',
        'created_at',
        'retention_until',
        'image_preview',
    )
    fieldsets = (
        ('Event Details', {
            'fields': ('id', 'user', 'event_type', 'captured_at', 'request_id', 'nonce'),
        }),
        ('Image & Verification', {
            'fields': ('image', 'image_preview', 'verification_status', 'face_recognition_status', 'face_confidence'),
        }),
        ('Network & Context', {
            'fields': ('ip_address', 'user_agent'),
        }),
        ('Retention & Audit', {
            'fields': ('retention_until', 'created_at'),
        }),
    )
    actions = ['override_verification_approved', 'override_verification_rejected', 'toggle_retention_flag']
    date_hierarchy = 'captured_at'

    def request_id_link(self, obj):
        """Display request_id as a link to the full record."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:security_photos_securityphoto_change', args=[obj.id]),
            obj.request_id or 'No ID',
        )
    request_id_link.short_description = 'Request ID'

    def verification_status_colored(self, obj):
        """Display verification status with color coding."""
        color_map = {
            'VALIDATED': '#28a745',
            'REJECTED': '#dc3545',
            'PENDING': '#ffc107',
            'PROCESSING': '#17a2b8',
        }
        color = color_map.get(obj.verification_status, '#6c757d')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_verification_status_display(),
        )
    verification_status_colored.short_description = 'Verification Status'

    def image_preview(self, obj):
        """Display a thumbnail preview of the security photo."""
        if obj.image:
            return format_html(
                '<img src="{}" width="200" height="200" style="border-radius: 5px; border: 1px solid #ddd;" />',
                obj.image.url,
            )
        return 'No image'
    image_preview.short_description = 'Photo Preview'

    @admin.action(description='Override: Mark as VALIDATED')
    def override_verification_approved(self, request, queryset):
        """Admin can manually override verification status to VALIDATED."""
        updated = queryset.exclude(verification_status='VALIDATED').update(verification_status='VALIDATED')
        self.message_user(
            request,
            f'{updated} security photo(s) marked as VALIDATED.',
            messages.SUCCESS,
        )

    @admin.action(description='Override: Mark as REJECTED')
    def override_verification_rejected(self, request, queryset):
        """Admin can manually override verification status to REJECTED."""
        updated = queryset.exclude(verification_status='REJECTED').update(verification_status='REJECTED')
        self.message_user(
            request,
            f'{updated} security photo(s) marked as REJECTED.',
            messages.WARNING,
        )

    @admin.action(description='Toggle retention hold (extend to 90 days)')
    def toggle_retention_flag(self, request, queryset):
        """Toggle retention hold flag for photos that need extended keeping."""
        retention_date = timezone.now() + timezone.timedelta(days=90)
        updated = 0
        for photo in queryset:
            if photo.retention_until is None or photo.retention_until < timezone.now():
                photo.retention_until = retention_date
                photo.save(update_fields=['retention_until'])
                updated += 1
        self.message_user(
            request,
            f'{updated} security photo(s) retention hold extended to 90 days.',
            messages.INFO,
        )

    def has_add_permission(self, request):
        """Prevent admins from manually creating security photo records."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Only staff can delete; require explicit action."""
        return request.user.is_superuser


@admin.register(ProfilePhoto)
class ProfilePhotoAdmin(admin.ModelAdmin):
    """Admin interface for profile photos (separate from security audit trail)."""

    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('id', 'user', 'created_at', 'updated_at', 'image_preview')
    fieldsets = (
        ('Profile Photo', {
            'fields': ('id', 'user', 'image', 'image_preview'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def image_preview(self, obj):
        """Display a thumbnail preview of the profile photo."""
        if obj.image:
            return format_html(
                '<img src="{}" width="150" height="150" style="border-radius: 50%; border: 2px solid #0b3d91;" />',
                obj.image.url,
            )
        return 'No image'
    image_preview.short_description = 'Photo Preview'

    def has_add_permission(self, request):
        """Profile photos are created via user flows, not manually."""
        return False
