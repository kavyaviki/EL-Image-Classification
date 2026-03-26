from django.urls import path
from . import views

app_name = 'inspections'

urlpatterns = [
    # Main pages
    path('', views.inspection_list, name='list'),
    path('upload/', views.upload_page, name='upload'),
    path('<uuid:pk>/', views.inspection_detail, name='detail'),
    path('analytics/', views.analytics_dashboard, name='analytics'),
    path('review-queue/', views.review_queue, name='review_queue'),
    path('image/<uuid:inspection_id>/', views.serve_image, name='serve_image'),
    
    # API endpoints
    path('api/upload/', views.upload_inspection, name='api_upload'),
    path('api/status/<uuid:job_id>/', views.check_job_status, name='api_status'),
    path('api/override/<uuid:pk>/', views.human_override, name='api_override'),
]