from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('generate_image/', views.generate_image_view, name='generate_image'),
    path('bulk/', views.bulk_image_generator, name='bulk_image_generator'),
    path('bulk/list/', views.bulk_list, name='bulk_list'),
    path('bulk/status/<int:bulk_request_id>/', views.bulk_status, name='bulk_status'),
    path('api/bulk_status/<int:bulk_request_id>/', views.get_bulk_status, name='get_bulk_status'),
    path('api/bulk/<int:request_id>/delete/', views.delete_bulk_request, name='delete_bulk_request'),
    path('api/prompt/<int:prompt_id>/retry/', views.retry_failed_prompt, name='retry_failed_prompt'),
    path('api/bulk/<int:bulk_request_id>/retry-failed/', views.retry_all_failed, name='retry_all_failed'),
    path('api/bulk/<int:bulk_request_id>/download/', views.download_all_images, name='download_all_images'),
    path('api/prompt/<int:prompt_id>/mark-completed/', views.mark_prompt_completed, name='mark_prompt_completed'),
    path('api/bulk/<int:bulk_request_id>/reset-stuck/', views.reset_stuck_prompts, name='reset_stuck_prompts'),
    path('api/bulk/delete-multiple/', views.bulk_delete_requests, name='bulk_delete_requests'),
    path('api/bulk/download-multiple/', views.bulk_download_requests, name='bulk_download_requests'),
    path('settings/', views.whisk_settings, name='whisk_settings'),
    path('settings/imagefx/', views.imagefx_settings, name='imagefx_settings'),
    path('settings/view/', views.settings_view, name='settings_view'),
]
