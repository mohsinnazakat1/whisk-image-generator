from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('generate_image/', views.generate_image_view, name='generate_image'),
    path('bulk/', views.bulk_image_generator, name='bulk_image_generator'),
    path('bulk/status/<int:bulk_request_id>/', views.bulk_status, name='bulk_status'),
    path('api/bulk_status/<int:bulk_request_id>/', views.get_bulk_status, name='get_bulk_status'),
]
