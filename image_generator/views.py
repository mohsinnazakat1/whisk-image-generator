from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.contrib import messages
from .models import BulkImageRequest, ImagePrompt, WhiskSettings
from .forms import WhiskSettingsForm
from .tasks import generate_image_task
from . import whisk
import zipfile
import io
import base64
import re
import json
import logging

logger = logging.getLogger(__name__)

def index(request):
    # Check if Whisk settings are configured
    whisk_settings = WhiskSettings.get_settings()
    settings_configured = bool(whisk_settings.auth_token and whisk_settings.project_id)
    
    return render(request, 'image_generator/index.html', {
        'settings_configured': settings_configured
    })

def generate_image_view(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        if not prompt:
            return render(request, 'image_generator/index.html', {'error': 'Prompt is required.'})

        try:
            # Check if settings are configured
            whisk_settings = WhiskSettings.get_settings()
            if not whisk_settings.auth_token or not whisk_settings.project_id:
                return render(request, 'image_generator/index.html', {
                    'error': 'Please configure your Whisk API settings first. Go to Settings to add your auth token and project ID.',
                    'prompt': prompt
                })

            # Generate image using database settings
            image_data = whisk.generate_image(prompt)
            if not image_data:
                raise Exception('Failed to generate image')

            # Extract the first image URL
            image_url = None
            for panel in image_data.get('imagePanels', []):
                for image in panel.get('generatedImages', []):
                    image_url = f"data:image/png;base64,{image.get('encodedImage')}"
                    break
                if image_url:
                    break

            if not image_url:
                raise Exception('No image generated')

            # Return to the same page with the generated image
            return render(request, 'image_generator/index.html', {
                'generated_image': image_url,
                'prompt': prompt
            })

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return render(request, 'image_generator/index.html', {
                'error': str(e) if settings.DEBUG else 'Failed to generate image. Please try again.',
                'prompt': prompt
            })
    else:
        return render(request, 'image_generator/index.html')

def bulk_list(request):
    """View to list all bulk image generation requests"""
    bulk_requests = BulkImageRequest.objects.annotate(
        completed_count=Count('prompts', filter=Q(prompts__status='completed')),
        total_count=Count('prompts')
    ).order_by('-created_at')
    
    return render(request, 'image_generator/bulk_list.html', {
        'bulk_requests': bulk_requests
    })

@require_http_methods(["DELETE"])
def delete_bulk_request(request, request_id):
    """Delete a bulk request and all its associated images"""
    try:
        bulk_request = get_object_or_404(BulkImageRequest, id=request_id)
        bulk_request.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Error deleting bulk request {request_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def bulk_image_generator(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        prompts_str = request.POST.get('prompts', '')
        
        if not title:
            return render(request, 'image_generator/bulk_generator.html', {
                'error': 'Title is required for bulk generation.',
                'prompts': prompts_str
            })
        
        try:
            prompts = json.loads(prompts_str)
            if not isinstance(prompts, list):
                raise ValueError("Input must be a JSON array of strings.")
        except (json.JSONDecodeError, ValueError) as e:
            return render(request, 'image_generator/bulk_generator.html', {
                'error': str(e),
                'title': title,
                'prompts': prompts_str
            })

        bulk_request = BulkImageRequest.objects.create(title=title, status='processing')
        for prompt_text in prompts:
            image_prompt = ImagePrompt.objects.create(
                bulk_request=bulk_request,
                prompt_text=prompt_text
            )
            generate_image_task.delay(image_prompt.id)
        
        # Check if all tasks are completed to update the bulk request status
        # This is a simplified check; a more robust solution might use Celery chains or groups
        all_prompts = ImagePrompt.objects.filter(bulk_request=bulk_request)
        if all(p.status == 'completed' for p in all_prompts):
            bulk_request.status = 'completed'
            bulk_request.save()

        return redirect('bulk_status', bulk_request_id=bulk_request.id)
    
    return render(request, 'image_generator/bulk_generator.html')

def bulk_status(request, bulk_request_id):
    bulk_request = BulkImageRequest.objects.get(id=bulk_request_id)
    return render(request, 'image_generator/bulk_status.html', {'bulk_request': bulk_request})

def get_bulk_status(request, bulk_request_id):
    bulk_request = BulkImageRequest.objects.get(id=bulk_request_id)
    prompts = bulk_request.prompts.all().values('id', 'prompt_text', 'status', 'generated_image')
    
    # Calculate status counts
    status_counts = bulk_request.prompts.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        failed=Count('id', filter=Q(status='failed')),
        processing=Count('id', filter=Q(status='processing')),
        pending=Count('id', filter=Q(status='pending'))
    )
    
    return JsonResponse({
        'status': bulk_request.get_status_display(),
        'prompts': list(prompts),
        'counts': status_counts
    })

def download_all_images(request, bulk_request_id):
    """Download all generated images as a ZIP file"""
    bulk_request = get_object_or_404(BulkImageRequest, id=bulk_request_id)
    
    # Create a BytesIO buffer to store the ZIP file
    buffer = io.BytesIO()
    
    # Get completed prompts in the order they were created (same order as input array)
    completed_prompts = bulk_request.prompts.filter(status='completed').order_by('id')
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for index, prompt in enumerate(completed_prompts, 1):
            if prompt.generated_image:
                # Extract the base64 data from the data URL
                match = re.match(r'data:image/(\w+);base64,(.+)', prompt.generated_image)
                if match:
                    image_format, image_data = match.groups()
                    
                    # Create filename with sequence number and bulk title
                    # Format: 001_{bulk_title}, 002_{bulk_title}, etc.
                    sanitized_title = re.sub(r'[^\w\s-]', '', bulk_request.title)
                    sanitized_title = re.sub(r'[-\s]+', '_', sanitized_title).strip('_')
                    filename = f"{index:03d}_{sanitized_title}.{image_format}"
                    
                    # Decode base64 and write to zip
                    try:
                        image_content = base64.b64decode(image_data)
                        zip_file.writestr(filename, image_content)
                    except Exception as e:
                        logger.error(f"Error processing image for prompt {prompt.id}: {str(e)}")
    
    # Prepare the response with bulk title in zip filename
    buffer.seek(0)
    sanitized_title = re.sub(r'[^\w\s-]', '', bulk_request.title)
    sanitized_title = re.sub(r'[-\s]+', '_', sanitized_title).strip('_')
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename={sanitized_title}_images.zip'
    
    return response

@require_http_methods(["POST"])
def retry_failed_prompt(request, prompt_id):
    """Retry a single failed image prompt"""
    try:
        prompt = get_object_or_404(ImagePrompt, id=prompt_id)
        if prompt.status == 'failed':
            prompt.status = 'pending'
            prompt.save()
            generate_image_task.delay(prompt.id)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Only failed prompts can be retried'}, status=400)
    except Exception as e:
        logger.error(f"Error retrying prompt {prompt_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_http_methods(["POST"])
def retry_all_failed(request, bulk_request_id):
    """Retry all failed image prompts in a bulk request"""
    try:
        bulk_request = get_object_or_404(BulkImageRequest, id=bulk_request_id)
        failed_prompts = bulk_request.prompts.filter(status='failed')
        for prompt in failed_prompts:
            prompt.status = 'pending'
            prompt.save()
            generate_image_task.delay(prompt.id)
        return JsonResponse({'status': 'success', 'retried_count': failed_prompts.count()})
    except Exception as e:
        logger.error(f"Error retrying failed prompts for bulk request {bulk_request_id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def whisk_settings(request):
    """View to display and update Whisk API settings"""
    settings_obj = WhiskSettings.get_settings()
    
    if request.method == 'POST':
        form = WhiskSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Whisk settings updated successfully!')
            return redirect('whisk_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = WhiskSettingsForm(instance=settings_obj)
    
    return render(request, 'image_generator/whisk_settings.html', {
        'form': form,
        'settings': settings_obj
    })

def settings_view(request):
    """View current settings (read-only)"""
    settings_obj = WhiskSettings.get_settings()
    return render(request, 'image_generator/settings_view.html', {
        'settings': settings_obj
    })