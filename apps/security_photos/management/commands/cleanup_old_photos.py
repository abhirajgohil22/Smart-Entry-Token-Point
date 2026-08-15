"""Management command to clean up old security photos per privacy policy."""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.security_photos.models import SecurityPhoto

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Delete security photos older than the specified retention period (default 30 days).

    Photos with retention_until set (admin-flagged for investigation) are preserved.
    This command respects privacy compliance and GDPR data minimization principles.
    """

    help = 'Delete security photos older than specified days, respecting retention holds.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete photos older than N days (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        cutoff_date = timezone.now() - timedelta(days=days)

        # Find photos older than cutoff that are NOT flagged for retention
        expired_photos = SecurityPhoto.objects.filter(
            captured_at__lt=cutoff_date,
        ).exclude(
            retention_until__gt=timezone.now(),
        )

        count = expired_photos.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired photos to delete.'))
            logger.info(f'Photo cleanup: No expired photos older than {days} days.')
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {count} photo(s) older than {days} days.')
            )
            for photo in expired_photos[:10]:
                self.stdout.write(f'  - {photo.request_id} ({photo.event_type}) / {photo.user.email}')
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
            logger.info(f'Photo cleanup dry-run: {count} photos would be deleted.')
            return

        # Delete photos and their associated image files
        for photo in expired_photos:
            if photo.image:
                try:
                    photo.image.delete(save=False)
                except Exception as exc:
                    logger.warning(f'Failed to delete image for photo {photo.id}: {exc}')

        deleted_count, _ = expired_photos.delete()

        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} security photo(s).')
        )
        logger.info(
            f'Photo cleanup: Deleted {deleted_count} photos older than {days} days. '
            f'Retained {SecurityPhoto.objects.filter(retention_until__gt=timezone.now()).count()} photos with hold flags.'
        )
