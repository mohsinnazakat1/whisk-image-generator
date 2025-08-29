from django.core.management.base import BaseCommand
from image_generator.models import BulkImageRequest, ImagePrompt
from django.db.models import Count, Q


class Command(BaseCommand):
    help = 'Debug bulk request statistics discrepancy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--bulk-id',
            type=int,
            required=True,
            help='Bulk request ID to debug',
        )

    def handle(self, *args, **options):
        bulk_id = options['bulk_id']
        
        try:
            bulk_request = BulkImageRequest.objects.get(id=bulk_id)
            self.stdout.write(f'Bulk Request: {bulk_request.title}')
            self.stdout.write(f'Status: {bulk_request.status}')
            self.stdout.write('')

            # Get all prompts for this bulk request
            prompts = bulk_request.prompts.all()
            self.stdout.write(f'Total prompts: {prompts.count()}')
            self.stdout.write('')

            # Count by status using aggregate (like bulk_status view)
            status_counts = bulk_request.prompts.aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='completed')),
                failed=Count('id', filter=Q(status='failed')),
                processing=Count('id', filter=Q(status='processing')),
                pending=Count('id', filter=Q(status='pending'))
            )
            self.stdout.write('Status counts (aggregate method - used in bulk_status view):')
            for status, count in status_counts.items():
                self.stdout.write(f'  {status}: {count}')
            self.stdout.write('')

            # Count by status using annotations (like bulk_list view)
            bulk_with_counts = BulkImageRequest.objects.filter(id=bulk_id).annotate(
                completed_count=Count('prompts', filter=Q(prompts__status='completed')),
                failed_count=Count('prompts', filter=Q(prompts__status='failed')),
                processing_count=Count('prompts', filter=Q(prompts__status='processing')),
                pending_count=Count('prompts', filter=Q(prompts__status='pending')),
                total_count=Count('prompts')
            ).first()

            self.stdout.write('Status counts (annotation method - used in bulk_list view):')
            self.stdout.write(f'  completed: {bulk_with_counts.completed_count}')
            self.stdout.write(f'  failed: {bulk_with_counts.failed_count}')
            self.stdout.write(f'  processing: {bulk_with_counts.processing_count}')
            self.stdout.write(f'  pending: {bulk_with_counts.pending_count}')
            self.stdout.write(f'  total: {bulk_with_counts.total_count}')
            self.stdout.write('')

            # Show actual status distribution
            self.stdout.write('Actual status distribution (direct count):')
            for status in ['pending', 'processing', 'completed', 'failed']:
                count = prompts.filter(status=status).count()
                self.stdout.write(f'  {status}: {count}')
            self.stdout.write('')

            # Show individual prompt statuses
            self.stdout.write('Individual prompt statuses:')
            for i, prompt in enumerate(prompts.order_by('id'), 1):
                self.stdout.write(f'  #{i}: {prompt.status} - {prompt.prompt_text[:50]}...')

        except BulkImageRequest.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Bulk request with ID {bulk_id} not found')
            )