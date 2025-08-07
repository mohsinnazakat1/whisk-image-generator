from celery import shared_task
from .models import ImagePrompt
from . import whisk
import logging

logger = logging.getLogger(__name__)

@shared_task
def generate_image_task(prompt_id):
    try:
        image_prompt = ImagePrompt.objects.get(id=prompt_id)
        image_prompt.status = 'processing'
        image_prompt.save()

        auth_token = whisk.get_authorization_token()
        if not auth_token:
            raise Exception('Failed to get authorization token.')

        project_id = whisk.get_new_project_id('Bulk Generation')
        if not project_id:
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
