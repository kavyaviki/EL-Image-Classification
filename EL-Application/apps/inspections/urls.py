from django.urls import path
from . import views

app_name = 'inspections'

urlpatterns = [
    # ============================================================
    # API ENDPOINTS - Place all API routes first
    # ============================================================
    path('api/upload/', views.upload_inspection, name='api_upload'),
    path('api/status/<uuid:job_id>/', views.check_job_status, name='api_status'),
    path('api/override/<uuid:pk>/', views.human_override, name='api_override'),
    path('api/export/', views.export_inspections, name='api_export'),
    
    # ============================================================
    # MAIN PAGE VIEWS - Specific static paths
    # ============================================================
    path('', views.inspection_list, name='list'),
    path('upload/', views.upload_page, name='upload'),
    path('analytics/', views.analytics_dashboard, name='analytics'),
    path('review-queue/', views.review_queue, name='review_queue'),
    
    # ============================================================
    # IMAGE SERVING - Has UUID but specific prefix
    # ============================================================
    path('image/<uuid:inspection_id>/', views.serve_image, name='serve_image'),
    
    # ============================================================
    # CATCH-ALL UUID PATTERN - This must be LAST
    # This will match any UUID that hasn't been matched by previous patterns
    # ============================================================
    path('<uuid:pk>/', views.inspection_detail, name='detail'),
]