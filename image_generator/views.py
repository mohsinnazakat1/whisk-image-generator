from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import BulkImageRequest, ImagePrompt
from .tasks import generate_image_task
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
            # This view is now simplified as the core logic is in the single image generator
            return render(request, 'image_generator/index.html', {'prompt': prompt, 'images': images, 'error': error})
    else:
        return render(request, 'image_generator/index.html')

def bulk_image_generator(request):
    if request.method == 'POST':
        prompts_str = request.POST.get('prompts', '')
        try:
            prompts = json.loads(prompts_str)
            if not isinstance(prompts, list):
                raise ValueError("Input must be a JSON array of strings.")
        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse({'error': str(e)}, status=400)

        bulk_request = BulkImageRequest.objects.create(status='processing')
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
    return JsonResponse({
        'status': bulk_request.get_status_display(),
        'prompts': list(prompts)
    })
