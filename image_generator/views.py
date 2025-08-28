from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.contrib import messages
from .models import BulkImageRequest, ImagePrompt, WhiskSettings, ImageFXSettings
from .forms import WhiskSettingsForm, ImageFXSettingsForm
from .tasks import generate_image_task
from . import whisk, imagefx
import zipfile
import io
import base64
import re
import json
import logging

logger = logging.getLogger(__name__)

def index(request):
    # Check if settings are configured for both APIs
    whisk_settings = WhiskSettings.get_settings()
    imagefx_settings = ImageFXSettings.get_settings()
    
    whisk_configured = bool(whisk_settings.auth_token and whisk_settings.project_id)
    imagefx_configured = bool(imagefx_settings.auth_token)
    
    return render(request, 'image_generator/index.html', {
        'whisk_configured': whisk_configured,
        'imagefx_configured': imagefx_configured,
        'settings_configured': whisk_configured or imagefx_configured
    })

def generate_image_view(request):
    if request.method == 'POST':
        prompt = request.POST.get('prompt')
        api_provider = request.POST.get('api_provider', 'whisk')
        
        if not prompt:
            return render(request, 'image_generator/index.html', {'error': 'Prompt is required.'})

        try:
            # Check settings based on selected API provider
            if api_provider == 'imagefx':
                imagefx_settings = ImageFXSettings.get_settings()
                if not imagefx_settings.auth_token:
                    return render(request, 'image_generator/index.html', {
                        'error': 'Please configure your ImageFX API settings first. Go to Settings to add your auth token.',
                        'prompt': prompt,
                        'api_provider': api_provider
                    })
                
                # Generate image using ImageFX
                image_data = imagefx.generate_image(prompt)
            else:
                # Default to Whisk
                whisk_settings = WhiskSettings.get_settings()
                if not whisk_settings.auth_token or not whisk_settings.project_id:
                    return render(request, 'image_generator/index.html', {
                        'error': 'Please configure your Whisk API settings first. Go to Settings to add your auth token and project ID.',
                        'prompt': prompt,
                        'api_provider': api_provider
                    })
                
                # Generate image using Whisk
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
                'prompt': prompt,
                'api_provider': api_provider,
                'whisk_configured': bool(WhiskSettings.get_settings().auth_token and WhiskSettings.get_settings().project_id),
                'imagefx_configured': bool(ImageFXSettings.get_settings().auth_token),
                'settings_configured': True
            })

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return render(request, 'image_generator/index.html', {
                'error': str(e) if settings.DEBUG else 'Failed to generate image. Please try again.',
                'prompt': prompt,
                'api_provider': api_provider,
                'whisk_configured': bool(WhiskSettings.get_settings().auth_token and WhiskSettings.get_settings().project_id),
                'imagefx_configured': bool(ImageFXSettings.get_settings().auth_token),
                'settings_configured': True
            })
    else:
        return render(request, 'image_generator/index.html')

def bulk_list(request):
    """View to list all bulk image generation requests with pagination, filtering, and statistics"""
    from django.core.paginator import Paginator
    from django.db.models import Sum
    
    # Get filter parameters
    api_provider = request.GET.get('api_provider', 'all')
    search_query = request.GET.get('search', '')
    page_number = request.GET.get('page', 1)
    
    # Base queryset with annotations
    bulk_requests = BulkImageRequest.objects.annotate(
        completed_count=Count('prompts', filter=Q(prompts__status='completed')),
        failed_count=Count('prompts', filter=Q(prompts__status='failed')),
        processing_count=Count('prompts', filter=Q(prompts__status='processing')),
        pending_count=Count('prompts', filter=Q(prompts__status='pending')),
        total_count=Count('prompts')
    )
    
    # Apply filters
    if api_provider != 'all':
        bulk_requests = bulk_requests.filter(api_provider=api_provider)
    
    if search_query:
        bulk_requests = bulk_requests.filter(title__icontains=search_query)
    
    # Order by creation date (newest first)
    bulk_requests = bulk_requests.order_by('-created_at')
    
    # Calculate statistics
    all_requests = BulkImageRequest.objects.all()
    stats = {
        'total_requests': all_requests.count(),
        'whisk_requests': all_requests.filter(api_provider='whisk').count(),
        'imagefx_requests': all_requests.filter(api_provider='imagefx').count(),
        'total_images': ImagePrompt.objects.count(),
        'completed_images': ImagePrompt.objects.filter(status='completed').count(),
        'processing_images': ImagePrompt.objects.filter(status='processing').count(),
        'failed_images': ImagePrompt.objects.filter(status='failed').count(),
    }
    
    # Pagination
    paginator = Paginator(bulk_requests, 10)  # 10 requests per page
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'image_generator/bulk_list.html', {
        'page_obj': page_obj,
        'bulk_requests': page_obj.object_list,
        'stats': stats,
        'current_api_provider': api_provider,
        'search_query': search_query,
        'paginator': paginator,
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

@require_http_methods(["POST"])
def bulk_delete_requests(request):
    """Delete multiple bulk requests"""
    try:
        import json
        data = json.loads(request.body)
        request_ids = data.get('request_ids', [])
        
        if not request_ids:
            return JsonResponse({'status': 'error', 'message': 'No requests selected'}, status=400)
        
        deleted_count = BulkImageRequest.objects.filter(id__in=request_ids).count()
        BulkImageRequest.objects.filter(id__in=request_ids).delete()
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Successfully deleted {deleted_count} bulk requests'
        })
    except Exception as e:
        logger.error(f"Error bulk deleting requests: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def bulk_download_requests(request):
    """Download images from multiple bulk requests as a ZIP file"""
    try:
        request_ids = request.GET.get('ids', '').split(',')
        request_ids = [int(id) for id in request_ids if id.isdigit()]
        
        if not request_ids:
            return JsonResponse({'status': 'error', 'message': 'No requests selected'}, status=400)
        
        bulk_requests = BulkImageRequest.objects.filter(id__in=request_ids)
        
        # Create a BytesIO buffer to store the ZIP file
        buffer = io.BytesIO()
        
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for bulk_request in bulk_requests:
                # Create folder for each bulk request
                folder_name = re.sub(r'[^\w\s-]', '', bulk_request.title)
                folder_name = re.sub(r'[-\s]+', '_', folder_name).strip('_')
                
                completed_prompts = bulk_request.prompts.filter(status='completed').order_by('id')
                
                for index, prompt in enumerate(completed_prompts, 1):
                    if prompt.generated_image:
                        # Extract the base64 data from the data URL
                        match = re.match(r'data:image/(\w+);base64,(.+)', prompt.generated_image)
                        if match:
                            image_format, image_data = match.groups()
                            
                            # Create filename with bulk request folder
                            filename = f"{folder_name}/{index:03d}_{folder_name}.{image_format}"
                            
                            # Decode base64 and write to zip
                            try:
                                image_content = base64.b64decode(image_data)
                                zip_file.writestr(filename, image_content)
                            except Exception as e:
                                logger.error(f"Error processing image for prompt {prompt.id}: {str(e)}")
        
        # Prepare the response
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename=bulk_images_{len(request_ids)}_requests.zip'
        
        return response
        
    except Exception as e:
        logger.error(f"Error bulk downloading requests: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def bulk_image_generator(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        prompts_str = request.POST.get('prompts', '')
        api_provider = request.POST.get('api_provider', 'whisk')
        
        if not title:
            return render(request, 'image_generator/bulk_generator.html', {
                'error': 'Title is required for bulk generation.',
                'prompts': prompts_str,
                'api_provider': api_provider
            })
        
        try:
            prompts = json.loads(prompts_str)
            if not isinstance(prompts, list):
                raise ValueError("Input must be a JSON array of strings.")
        except (json.JSONDecodeError, ValueError) as e:
            return render(request, 'image_generator/bulk_generator.html', {
                'error': str(e),
                'title': title,
                'prompts': prompts_str,
                'api_provider': api_provider
            })

        # Validate API provider settings
        if api_provider == 'imagefx':
            imagefx_settings = ImageFXSettings.get_settings()
            if not imagefx_settings.auth_token:
                return render(request, 'image_generator/bulk_generator.html', {
                    'error': 'Please configure your ImageFX API settings first.',
                    'title': title,
                    'prompts': prompts_str,
                    'api_provider': api_provider
                })
        else:
            whisk_settings = WhiskSettings.get_settings()
            if not whisk_settings.auth_token or not whisk_settings.project_id:
                return render(request, 'image_generator/bulk_generator.html', {
                    'error': 'Please configure your Whisk API settings first.',
                    'title': title,
                    'prompts': prompts_str,
                    'api_provider': api_provider
                })

        bulk_request = BulkImageRequest.objects.create(
            title=title, 
            status='processing',
            api_provider=api_provider
        )
        
        for prompt_text in prompts:
            image_prompt = ImagePrompt.objects.create(
                bulk_request=bulk_request,
                prompt_text=prompt_text,
                api_provider=api_provider
            )
            generate_image_task.delay(image_prompt.id)
        
        # Check if all tasks are completed to update the bulk request status
        # This is a simplified check; a more robust solution might use Celery chains or groups
        all_prompts = ImagePrompt.objects.filter(bulk_request=bulk_request)
        if all(p.status == 'completed' for p in all_prompts):
            bulk_request.status = 'completed'
            bulk_request.save()

        return redirect('bulk_status', bulk_request_id=bulk_request.id)
    
    # Check settings for both APIs
    whisk_settings = WhiskSettings.get_settings()
    imagefx_settings = ImageFXSettings.get_settings()
    
    return render(request, 'image_generator/bulk_generator.html', {
        'whisk_configured': bool(whisk_settings.auth_token and whisk_settings.project_id),
        'imagefx_configured': bool(imagefx_settings.auth_token)
    })

def bulk_status(request, bulk_request_id):
    bulk_request = BulkImageRequest.objects.get(id=bulk_request_id)
    # Get prompts in the correct order (by ID, which represents creation order)
    ordered_prompts = bulk_request.prompts.all().order_by('id')
    return render(request, 'image_generator/bulk_status.html', {
        'bulk_request': bulk_request,
        'ordered_prompts': ordered_prompts
    })

def get_bulk_status(request, bulk_request_id):
    bulk_request = BulkImageRequest.objects.get(id=bulk_request_id)
    
    # Get prompts in the correct order (by ID, which represents creation order)
    ordered_prompts = bulk_request.prompts.all().order_by('id')
    
    # Add sequential numbering to each prompt
    prompts_with_numbers = []
    for index, prompt in enumerate(ordered_prompts, 1):
        prompts_with_numbers.append({
            'id': prompt.id,
            'prompt_text': prompt.prompt_text,
            'status': prompt.status,
            'generated_image': prompt.generated_image,
            'sequence_number': index
        })
    
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
        'prompts': prompts_with_numbers,
        'counts': status_counts
    })

def download_all_images(request, bulk_request_id):
    """Download all generated images as a ZIP file with summary"""
    bulk_request = get_object_or_404(BulkImageRequest, id=bulk_request_id)
    
    # Create a BytesIO buffer to store the ZIP file
    buffer = io.BytesIO()
    
    # Get all prompts in the order they were created
    all_prompts = bulk_request.prompts.all().order_by('id')
    completed_prompts = all_prompts.filter(status='completed')
    failed_prompts = all_prompts.filter(status='failed')
    
    # Calculate statistics
    total_count = all_prompts.count()
    completed_count = completed_prompts.count()
    failed_count = failed_prompts.count()
    processing_count = all_prompts.filter(status='processing').count()
    pending_count = all_prompts.filter(status='pending').count()
    
    # Create summary text content
    summary_content = f"""BULK IMAGE GENERATION SUMMARY
=====================================

Project Title: {bulk_request.title}
Generated on: {bulk_request.created_at.strftime('%Y-%m-%d %H:%M:%S')}

STATISTICS:
-----------
Total Images: {total_count}
Completed: {completed_count}
Failed: {failed_count}
Processing: {processing_count}
Pending: {pending_count}

SUCCESS RATE: {(completed_count/total_count*100):.1f}%

"""
    
    if failed_count > 0:
        summary_content += "\nFAILED IMAGES:\n"
        summary_content += "-" * 50 + "\n"
        for index, prompt in enumerate(all_prompts, 1):
            if prompt.status == 'failed':
                summary_content += f"#{index:03d}: {prompt.prompt_text}\n"
    
    if completed_count > 0:
        summary_content += f"\nSUCCESSFUL IMAGES ({completed_count} files):\n"
        summary_content += "-" * 50 + "\n"
        for index, prompt in enumerate(all_prompts, 1):
            if prompt.status == 'completed':
                summary_content += f"#{index:03d}: {prompt.prompt_text}\n"
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add summary text file
        zip_file.writestr('SUMMARY.txt', summary_content.encode('utf-8'))
        
        # Add completed images
        for index, prompt in enumerate(all_prompts, 1):
            if prompt.status == 'completed' and prompt.generated_image:
                # Extract the base64 data from the data URL
                match = re.match(r'data:image/(\w+);base64,(.+)', prompt.generated_image)
                if match:
                    image_format, image_data = match.groups()
                    
                    # Create filename with sequence number matching the prompt order
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

@require_http_methods(["POST"])
def mark_prompt_completed(request, prompt_id):
    """Manually mark a prompt as completed (for stuck processing tasks)"""
    try:
        prompt = get_object_or_404(ImagePrompt, id=prompt_id)
        if prompt.status == 'processing':
            prompt.status = 'completed'
            prompt.save()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Only processing prompts can be marked as completed'}, status=400)
    except Exception as e:
        logger.error(f"Error marking prompt {prompt_id} as completed: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_http_methods(["POST"])
def reset_stuck_prompts(request, bulk_request_id):
    """Reset all stuck processing prompts in a bulk request"""
    try:
        bulk_request = get_object_or_404(BulkImageRequest, id=bulk_request_id)
        from datetime import timedelta
        from django.utils import timezone
        
        # Find prompts stuck in processing for more than 5 minutes
        cutoff_time = timezone.now() - timedelta(minutes=5)
        stuck_prompts = bulk_request.prompts.filter(
            status='processing',
            updated_at__lt=cutoff_time
        )
        
        for prompt in stuck_prompts:
            prompt.status = 'pending'
            prompt.save()
            generate_image_task.delay(prompt.id)
            
        return JsonResponse({'status': 'success', 'reset_count': stuck_prompts.count()})
    except Exception as e:
        logger.error(f"Error resetting stuck prompts for bulk request {bulk_request_id}: {str(e)}")
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
    whisk_settings = WhiskSettings.get_settings()
    imagefx_settings = ImageFXSettings.get_settings()
    return render(request, 'image_generator/settings_view.html', {
        'whisk_settings': whisk_settings,
        'imagefx_settings': imagefx_settings
    })

def imagefx_settings(request):
    """View to display and update ImageFX API settings"""
    settings_obj = ImageFXSettings.get_settings()
    
    if request.method == 'POST':
        form = ImageFXSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'ImageFX settings updated successfully!')
            return redirect('imagefx_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ImageFXSettingsForm(instance=settings_obj)
    
    return render(request, 'image_generator/imagefx_settings.html', {
        'form': form,
        'settings': settings_obj
    })