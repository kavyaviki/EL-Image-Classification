# inspections/views.py
"""
Views for the Inspections app.
Handles all user-facing pages and API endpoints for image upload, review, and results.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Inspection, HumanOverride
from .ai_client import AIServiceClient
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================================
# PAGE VIEWS (Return HTML pages)
# ============================================================================

@login_required
def upload_page(request):
    """
    Render the image upload page.
    
    This view displays the upload interface where users can drag & drop images.
    It also shows the 5 most recent uploads for quick reference.
    
    URL: /inspections/upload/
    Template: inspections/upload.html
    
    Returns:
        HttpResponse: Rendered upload page with recent inspections
    """
    # Get the 5 most recent inspections for the current user
    recent_inspections = Inspection.objects.filter(
        uploaded_by=request.user
    ).order_by('-uploaded_at')[:5]
    
    return render(request, 'inspections/upload.html', {
        'recent_inspections': recent_inspections
    })


@login_required
def inspection_list(request):
    """
    Display a paginated list of all inspections for the current user.
    
    Supports filtering by:
    - Search (by filename)
    - Status (good, defect, review, pending, failed)
    - Date range (from_date and to_date)
    
    Also handles the dynamic "review" status based on confidence threshold.
    
    URL: /inspections/
    Template: inspections/list.html
    
    Returns:
        HttpResponse: Rendered list page with paginated inspections
    """
    # Get review threshold from settings (configurable in .env)
    # Default: 0.8 (80%)
    review_threshold = getattr(settings, 'REVIEW_CONFIDENCE_THRESHOLD', 0.8)
    try:
        review_threshold = float(review_threshold)
    except (ValueError, TypeError):
        review_threshold = 0.8
    
    # Start with all inspections for the current user
    inspections = Inspection.objects.filter(uploaded_by=request.user)
    
    # ============================================================
    # APPLY FILTERS
    # ============================================================
    
    # 1. Search by filename
    search = request.GET.get('search')
    if search:
        inspections = inspections.filter(name__icontains=search)
    
    # 2. Status filter (Good, Defective, Review, Pending, Failed)
    status_filter = request.GET.get('status')
    if status_filter:
        if status_filter == 'good':
            # Good: completed, confidence >= threshold, classification = 'good'
            inspections = inspections.filter(
                status='completed',
                ai_classification='good',
                ai_confidence__gte=review_threshold
            )
        elif status_filter == 'defect':
            # Defective: completed, confidence >= threshold, classification = 'defect'
            inspections = inspections.filter(
                status='completed',
                ai_classification='defect',
                ai_confidence__gte=review_threshold
            )
        elif status_filter == 'review':
            # Review: completed, confidence < threshold (needs human review)
            inspections = inspections.filter(
                status='completed',
                ai_confidence__lt=review_threshold
            )
        elif status_filter == 'pending':
            # Pending: queued or processing
            inspections = inspections.filter(status__in=['queued', 'processing'])
        elif status_filter == 'failed':
            # Failed: failed status
            inspections = inspections.filter(status='failed')
    
    # 3. Date range filter
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        inspections = inspections.filter(uploaded_at__date__gte=date_from)
    if date_to:
        inspections = inspections.filter(uploaded_at__date__lte=date_to)
    
    # Order by most recent first
    inspections = inspections.order_by('-uploaded_at')
    
    # ============================================================
    # ADD DISPLAY STATUS (for consistent UI presentation)
    # ============================================================
    for inspection in inspections:
        if inspection.status == 'completed':
            if inspection.ai_confidence is not None and inspection.ai_confidence < review_threshold:
                inspection.display_status = 'review'  # Low confidence = needs review
            else:
                inspection.display_status = inspection.ai_classification if inspection.ai_classification else 'completed'
        elif inspection.status in ['queued', 'processing']:
            inspection.display_status = 'pending'
        elif inspection.status == 'failed':
            inspection.display_status = 'failed'
        else:
            inspection.display_status = inspection.status
    
    # ============================================================
    # PAGINATION - 10 items per page
    # ============================================================
    paginator = Paginator(inspections, 10)
    page = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'page_obj': page_obj,
        'review_threshold': review_threshold,
        'status_choices': Inspection.STATUS_CHOICES,
    }
    return render(request, 'inspections/list.html', context)


@login_required
def inspection_detail(request, pk):
    """
    Show detailed view of a single inspection.
    
    This page displays:
    - The original image (via presigned URL)
    - AI classification results (confidence, defects, explanation)
    - Human override form
    - Classification history
    
    If the inspection is still queued/processing, it attempts to fetch
    results from S3 and update the record automatically.
    
    URL: /inspections/<uuid:pk>/
    Template: inspections/detail.html
    
    Args:
        pk: UUID of the inspection to display
        
    Returns:
        HttpResponse: Rendered detail page with inspection data
    """
    # Get the inspection or return 404 if not found or not owned by user
    inspection = get_object_or_404(Inspection, pk=pk, uploaded_by=request.user)
    
    # ============================================================
    # AUTO-FETCH RESULTS IF STILL PENDING
    # ============================================================
    if inspection.status in ['queued', 'processing'] and inspection.job_id:
        ai_client = AIServiceClient()
        results = ai_client.get_results_from_s3(
            str(inspection.job_id),
            inspection.name
        )
        
        if results:
            # Update inspection with AI results
            inspection.status = 'completed'
            inspection.ai_classification = results.get('prediction')
            inspection.ai_confidence = results.get('confidence')
            inspection.ai_processed_at = results.get('processed_at')
            
            # # Store defects as JSON if present
            # if results.get('defects'):
            #     import json
            #     inspection.ai_explanation = json.dumps(results.get('defects'))
            
            inspection.save()
    
    # ============================================================
    # CHECK FOR HUMAN OVERRIDE
    # ============================================================
    try:
        override = inspection.override
    except HumanOverride.DoesNotExist:
        override = None
    
    # ============================================================
    # CHECK WHERE USER CAME FROM (for back button navigation)
    # ============================================================
    # If coming from review queue, back button goes to review queue
    # If coming from results dashboard, back button goes to results list
    from_review_queue = request.GET.get('from_review_queue', 'false') == 'true'
    
    context = {
        'inspection': inspection,
        'override': override,
        'defects': [],
        'from_review_queue': from_review_queue,
    }
    return render(request, 'inspections/detail.html', context)


@login_required
def review_queue(request):
    """
    Display inspections that need human review.
    
    Review items are defined as:
    - Status = 'completed'
    - AI confidence < REVIEW_CONFIDENCE_THRESHOLD (default 80%)
    
    This is different from a status-based review queue; it's based on
    confidence scores, which is more dynamic.
    
    URL: /inspections/review-queue/
    Template: inspections/review_queue.html
    
    Returns:
        HttpResponse: Rendered review queue page
    """
    # Get review threshold from settings
    review_threshold = getattr(settings, 'REVIEW_CONFIDENCE_THRESHOLD', 0.8)
    try:
        review_threshold = float(review_threshold)
    except (ValueError, TypeError):
        review_threshold = 0.8
    
    # ============================================================
    # QUERY FOR ITEMS NEEDING REVIEW
    # ============================================================
    # Only completed inspections with confidence below threshold
    inspections = Inspection.objects.filter(
        uploaded_by=request.user,
        status='completed',                # Must be processed by AI
        ai_confidence__lt=review_threshold  # Low confidence = needs review
    )
    
    # ============================================================
    # APPLY FILTERS
    # ============================================================
    
    # Search by filename
    search = request.GET.get('search')
    if search:
        inspections = inspections.filter(name__icontains=search)
    
    # Review status filter (pending vs reviewed)
    review_status = request.GET.get('review_status')
    if review_status == 'pending':
        inspections = inspections.filter(human_override=False)
    elif review_status == 'reviewed':
        inspections = inspections.filter(human_override=True)
    
    # Date range filter
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        inspections = inspections.filter(uploaded_at__date__gte=date_from)
    if date_to:
        inspections = inspections.filter(uploaded_at__date__lte=date_to)
    
    # Order by most recent first
    inspections = inspections.order_by('-uploaded_at')
    
    # ============================================================
    # CALCULATE SUMMARY CARD COUNTS
    # ============================================================
    total_count = inspections.count()
    reviewed_count = inspections.filter(human_override=True).count()
    pending_count = total_count - reviewed_count
    
    # ============================================================
    # ADD DISPLAY STATUS FOR TEMPLATE
    # ============================================================
    for inspection in inspections:
        if inspection.ai_confidence is not None and inspection.ai_confidence < review_threshold:
            inspection.display_status = 'review'
        else:
            inspection.display_status = inspection.ai_classification if inspection.ai_classification else 'completed'
    
    # ============================================================
    # PAGINATION - 10 items per page
    # ============================================================
    paginator = Paginator(inspections, 10)
    page = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'page_obj': page_obj,
        'total_count': total_count,
        'reviewed_count': reviewed_count,
        'pending_count': pending_count,
        'review_threshold': review_threshold,
    }
    return render(request, 'inspections/review_queue.html', context)


@login_required
def analytics_dashboard(request):
    """
    Display analytics and insights dashboard.
    
    Shows statistics about:
    - Total inspections
    - Good vs Defective panels
    - Human override rate
    - Trend data over last 7 days
    
    URL: /inspections/analytics/
    Template: inspections/analytics.html
    
    Returns:
        HttpResponse: Rendered analytics dashboard
    """
    # ============================================================
    # BASIC STATISTICS
    # ============================================================
    total_inspections = Inspection.objects.filter(uploaded_by=request.user).count()
    
    good_count = Inspection.objects.filter(
        uploaded_by=request.user,
        ai_classification='good'
    ).count()
    
    defective_count = Inspection.objects.filter(
        uploaded_by=request.user,
        ai_classification='defect'
    ).count()
    
    override_count = Inspection.objects.filter(
        uploaded_by=request.user,
        human_override=True
    ).count()
    
    # Calculate percentages
    good_percentage = (good_count / total_inspections * 100) if total_inspections > 0 else 0
    defective_percentage = (defective_count / total_inspections * 100) if total_inspections > 0 else 0
    override_percentage = (override_count / total_inspections * 100) if total_inspections > 0 else 0
    
    # ============================================================
    # TREND DATA (LAST 7 DAYS)
    # ============================================================
    last_7_days = []
    for i in range(6, -1, -1):
        date = timezone.now().date() - timedelta(days=i)
        count = Inspection.objects.filter(
            uploaded_by=request.user,
            uploaded_at__date=date
        ).count()
        last_7_days.append({
            'date': date.strftime('%b %d'),
            'count': count
        })
    
    context = {
        'total_inspections': total_inspections,
        'good_count': good_count,
        'defective_count': defective_count,
        'override_count': override_count,
        'good_percentage': round(good_percentage, 1),
        'defective_percentage': round(defective_percentage, 1),
        'override_percentage': round(override_percentage, 1),
        'trend_data': last_7_days,
    }
    return render(request, 'inspections/analytics.html', context)


# ============================================================================
# IMAGE SERVING (For private S3 buckets)
# ============================================================================

@login_required
def serve_image(request, inspection_id):
    """
    Serve an image from private S3 bucket using a presigned URL.
    
    This view is used when the S3 bucket is private (block public access = ON).
    It generates a temporary, authenticated URL that allows the user to view
    the image. The URL expires after 1 hour.
    
    URL: /inspections/image/<uuid:inspection_id>/
    
    Args:
        inspection_id: UUID of the inspection whose image to serve
        
    Returns:
        HttpResponseRedirect: Redirects to the presigned URL
        Http404: If image not found or S3 key missing
        
    How it works:
        1. User visits /inspections/image/123/
        2. This view gets the inspection and its s3_key
        3. Generates a temporary presigned URL valid for 1 hour
        4. Redirects the user to that URL
        5. Browser loads the image from the temporary URL
    """
    # Get the inspection, ensuring it belongs to the current user
    inspection = get_object_or_404(Inspection, id=inspection_id, uploaded_by=request.user)
    
    # Check if we have an S3 key for this image
    if not inspection.s3_key:
        raise Http404("Image not found - no S3 key stored")
    
    # Generate presigned URL using the AI client
    ai_client = AIServiceClient()
    presigned_url = ai_client.get_presigned_image_url(inspection.s3_key, expiration=3600)
    
    if presigned_url:
        # Redirect to the temporary URL
        return redirect(presigned_url)
    
    raise Http404("Could not generate image URL")


# ============================================================================
# API ENDPOINTS (Return JSON for AJAX requests)
# ============================================================================

@login_required
@require_POST
def upload_inspection(request):
    """
    API endpoint to handle image uploads.
    
    This is called via AJAX from the upload page.
    It forwards images to the AI service and creates inspection records.
    
    URL: /inspections/api/upload/
    Method: POST
    
    Expected form data:
        images: One or more image files
    
    Returns:
        JsonResponse: Success status and job_id, or error message
        
    Flow:
        1. Get uploaded files from request
        2. Submit to AI service via ai_client.submit_images()
        3. Create Inspection records in database with status='queued'
        4. Return job_id to frontend for tracking
    """
    # Validate that files were uploaded
    if not request.FILES.getlist('images'):
        return JsonResponse({'error': 'No images uploaded'}, status=400)
    
    files = request.FILES.getlist('images')
    ai_client = AIServiceClient()
    
    # Submit to AI service
    result = ai_client.submit_images(files)
    
    if not result or not result.get('job_id'):
        return JsonResponse({'error': 'AI service submission failed'}, status=500)
    
    # Create inspection records for each file
    for file in files:
        # Construct the S3 key where the AI service will store the image
        # Format: uploads/{job_id}/{filename}
        s3_key = f"uploads/{result['job_id']}/{file.name}"
        
        Inspection.objects.create(
            name=file.name,
            uploaded_by=request.user,
            job_id=result['job_id'],
            status='queued',
            s3_key=s3_key  # Store for later image retrieval
        )
    
    return JsonResponse({
        'success': True,
        'job_id': result['job_id'],
        'file_count': result['file_count'],
        'message': result['message'],
        'status_check_url': result['status_check_url'],
    })


@login_required
def check_job_status(request, job_id):
    """
    API endpoint to check the status of a processing job.
    
    URL: /inspections/api/status/<uuid:job_id>/
    
    Args:
        job_id: The job ID to check
        
    Returns:
        JsonResponse: Status information or error
    """
    ai_client = AIServiceClient()
    status = ai_client.check_status(job_id)
    
    if status:
        return JsonResponse(status)
    
    return JsonResponse({'error': 'Job not found'}, status=404)


@login_required
@require_POST
def human_override(request, pk):
    """
    API endpoint to save a human override for an inspection.
    
    This is called when a user submits the override form on the detail page.
    It creates or updates a HumanOverride record and updates the inspection.
    
    URL: /inspections/api/override/<uuid:pk>/
    Method: POST
    
    Expected POST data:
        classification: 'good' or 'defect'
        reason: Why the override is being made
        notes: Optional additional notes
        
    Returns:
        JsonResponse: Success status and message
    """
    inspection = get_object_or_404(Inspection, pk=pk, uploaded_by=request.user)
    
    # Get data from POST
    classification = request.POST.get('classification')
    reason = request.POST.get('reason')
    notes = request.POST.get('notes', '')
    
    # Validate required fields
    if not classification or not reason:
        return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
    
    # Check if override already exists
    try:
        override = HumanOverride.objects.get(inspection=inspection)
        # Update existing override
        override.original_status = inspection.status
        override.original_classification = inspection.ai_classification
        override.new_status = 'completed'
        override.new_classification = classification
        override.reason = reason
        override.notes = notes
        override.overridden_by = request.user
        override.from_date = timezone.now()
        override.save()
        
    except HumanOverride.DoesNotExist:
        # Create new override
        override = HumanOverride.objects.create(
            inspection=inspection,
            overridden_by=request.user,
            original_status=inspection.status,
            original_classification=inspection.ai_classification,
            new_status='completed',
            new_classification=classification,
            reason=reason,
            notes=notes,
            from_date=timezone.now(),
        )
    
    # Update inspection
    inspection.human_override = True
    inspection.status = 'completed'
    inspection.ai_classification = classification
    inspection.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Override saved successfully',
        'override_id': str(override.id)
    })


@login_required
@require_POST
def update_inspection_status(request, pk):
    """
    API endpoint to update inspection status from review queue.
    
    This is called when a user selects a new status from the dropdown
    in the review queue table.
    
    URL: /inspections/api/update-status/<uuid:pk>/
    Method: POST
    
    Expected POST data:
        status: New status value
        notes: Optional notes
        
    Returns:
        JsonResponse: Success status and message
    """
    inspection = get_object_or_404(Inspection, pk=pk, uploaded_by=request.user)
    
    new_status = request.POST.get('status')
    
    if new_status:
        inspection.status = new_status
        inspection.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {new_status}',
            'new_status': new_status
        })
    
    return JsonResponse({
        'success': False,
        'error': 'No status provided'
    }, status=400)


# ============================================================================
# CONTEXT PROCESSOR (For sidebar badge count)
# ============================================================================

def review_queue_count(request):
    """
    Context processor to add review queue count to all templates.
    
    This allows the sidebar to display a badge showing how many items
    are pending review.
    
    Add to TEMPLATES context_processors in settings.py:
        'apps.inspections.views.review_queue_count'
        
    Returns:
        dict: {'review_queue_count': count}
    """
    if request.user.is_authenticated:
        # Count items with low confidence (need review)
        review_threshold = getattr(settings, 'REVIEW_CONFIDENCE_THRESHOLD', 0.8)
        count = Inspection.objects.filter(
            uploaded_by=request.user,
            status='completed',
            ai_confidence__lt=review_threshold,
            human_override=False  # Only count those not yet overridden
        ).count()
        return {'review_queue_count': count}
    return {'review_queue_count': 0}