from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from . import whisk
import json
import logging

logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'image_generator/index.html')

def generate_image_view(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        images = []
        error = None
        if not prompt:
            error = 'Prompt is required.'
        else:
            auth_token = whisk.get_authorization_token()
            if not auth_token:
                error = 'Failed to get authorization token. Check your WHISK_COOKIE.'
            else:
                project_id = whisk.get_new_project_id('New Project')
                if not project_id:
                    error = 'Failed to create new project. Check your WHISK_COOKIE.'
                else:
                    image_data = whisk.generate_image(prompt, auth_token, project_id)
                    logger.debug("Received response from Whisk API.")
                    if not image_data:
                        error = 'Failed to generate image (empty response).'
                    else:
                        try:
                            for panel in image_data.get('imagePanels', []):
                                for image in panel.get('generatedImages', []):
                                    images.append(f"data:image/png;base64,{image.get('encodedImage')}")
                            if not images:
                                logger.warning("Could not find images in the expected structure of the API response.")
                            else:
                                logger.debug(f"Successfully processed {len(images)} image(s).")
                        except Exception as e:
                            logger.exception("An error occurred while parsing the image data.")
                            error = 'Error parsing image data from API.'
        return render(request, 'image_generator/index.html', {'prompt': prompt, 'images': images, 'error': error})
    else:
        return render(request, 'image_generator/index.html')