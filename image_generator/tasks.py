from celery import shared_task
from .models import ImagePrompt
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
        
        # Get auth token
        try:
            auth_token = whisk.get_authorization_token()
            if not auth_token:
                raise Exception('Empty authorization token received')
            logger.info("Authorization token obtained successfully")
        except Exception as e:
            logger.error(f"Authorization failed: {str(e)}")
            raise Exception('Failed to get authorization token.')

        logger.info("Authorization token obtained successfully")
        
        project_id = whisk.get_new_project_id('Bulk Generation')
        if not project_id:
            logger.error("Project ID creation failed")
            raise Exception('Failed to create new project.')

        image_data = whisk.generate_image(image_prompt.prompt_text, auth_token, project_id)
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
