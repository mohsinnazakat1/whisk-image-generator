from django.core.management.base import BaseCommand
from image_generator.models import ImagePrompt, BulkImageRequest
from image_generator.tasks import generate_image_task
from datetime import datetime, timedelta
from django.utils import timezone


class Command(BaseCommand):
    help = 'Fix stuck image generation tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--bulk-id',
            type=int,
            help='Fix stuck images for a specific bulk request ID',
        )
        parser.add_argument(
            '--reset-all',
            action='store_true',
            help='Reset all stuck processing images to pending and retry',
        )
        parser.add_argument(
            '--older-than',
            type=int,
            default=10,
            help='Reset images stuck in processing for more than X minutes (default: 10)',
        )

    def handle(self, *args, **options):
        bulk_id = options.get('bulk_id')
        reset_all = options.get('reset_all')
        older_than_minutes = options.get('older_than')
        
        # Calculate cutoff time
        cutoff_time = timezone.now() - timedelta(minutes=older_than_minutes)
        
        if bulk_id:
            # Fix stuck images for specific bulk request
            try:
                bulk_request = BulkImageRequest.objects.get(id=bulk_id)
                stuck_prompts = bulk_request.prompts.filter(
                    status='processing',
                    updated_at__lt=cutoff_time
                )
            except BulkImageRequest.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Bulk request with ID {bulk_id} not found')
                )
                return
        elif reset_all:
            # Fix all stuck images across all bulk requests
            stuck_prompts = ImagePrompt.objects.filter(
                status='processing',
                updated_at__lt=cutoff_time
            )
        else:
            self.stdout.write(
                self.style.ERROR('Please specify either --bulk-id or --reset-all')
            )
            return

        if not stuck_prompts.exists():
            self.stdout.write(
                self.style.SUCCESS(f'No stuck images found (older than {older_than_minutes} minutes)')
            )
            return

        count = stuck_prompts.count()
        self.stdout.write(f'Found {count} stuck images to reset...')

        # Reset status and retry tasks
        for prompt in stuck_prompts:
            self.stdout.write(f'Resetting prompt ID {prompt.id}: {prompt.prompt_text[:50]}...')
            prompt.status = 'pending'
            prompt.save()
            
            # Retry the task
            generate_image_task.delay(prompt.id)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully reset and retried {count} stuck images')
        )

        # Update bulk request status if needed
        if bulk_id:
            bulk_request.status = 'processing'
            bulk_request.save()
            self.stdout.write(f'Updated bulk request {bulk_id} status to processing')