from celery import shared_task
from .models import ImagePrompt, WhiskSettings
from . import whisk
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    name='image_generator.tasks.generate_image_task',
    queue='image_generation'
)
def generate_image_task(self, prompt_id):
    logger.info(f"Task started for prompt_id: {prompt_id}")
    try:
        # Get the prompt
        try:
            image_prompt = ImagePrompt.objects.get(id=prompt_id)
        except ImagePrompt.DoesNotExist:
            logger.error(f"ImagePrompt with id {prompt_id} not found")
            return

        # Update status to processing
        image_prompt.status = 'processing'
        image_prompt.save()
        logger.info(f"Starting image generation for prompt {prompt_id}: {image_prompt.prompt_text}")
        
        # Check if settings are configured
        whisk_settings = WhiskSettings.get_settings()
        if not whisk_settings.auth_token or not whisk_settings.project_id:
            logger.error("Whisk settings not configured")
            raise Exception('Whisk API settings not configured. Please configure auth token and project ID.')
        
        logger.info("Using configured auth token and project ID from database")

        image_data = whisk.generate_image(image_prompt.prompt_text)
        if not image_data:
            raise Exception('Failed to generate image (empty response).')

        # Extract the first image from the response
        image_url = None
        for panel in image_data.get('imagePanels', []):
            for image in panel.get('generatedImages', []):
                image_url = f"data:image/png;base64,{image.get('encodedImage')}"
                break
            if image_url:
                break
        
        if image_url:
            image_prompt.generated_image = image_url
            image_prompt.status = 'completed'
        else:
            image_prompt.status = 'failed'

    except Exception as e:
        logger.error(f"Error generating image for prompt {prompt_id}: {e}")
        image_prompt.status = 'failed'
    
    finally:
        image_prompt.save()
        
        # Check if all prompts in the bulk request are completed
        bulk_request = image_prompt.bulk_request
        all_prompts = bulk_request.prompts.all()
        if all(p.status in ['completed', 'failed'] for p in all_prompts):
            bulk_request.status = 'completed'
            bulk_request.save()
            logger.info(f"Bulk request {bulk_request.id} marked as completed")
