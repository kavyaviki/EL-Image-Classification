# inspections/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Inspection, HumanOverride
from .ai_client import AIServiceClient
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@login_required
def upload_page(request):
    """Render the upload page"""
    recent_inspections = Inspection.objects.filter(
        uploaded_by=request.user
    ).order_by('-uploaded_at')[:5]
    
    return render(request, 'inspections/upload.html', {
        'recent_inspections': recent_inspections
    })


@login_required
@require_POST
def upload_inspection(request):
    """
    Handle image upload - forwards to AI service
    """
    if not request.FILES.getlist('images'):
        return JsonResponse({'error': 'No images uploaded'}, status=400)
    
    files = request.FILES.getlist('images')
    ai_client = AIServiceClient()
    
    # Submit to AI service
    result = ai_client.submit_images(files)
    
    if not result or not result.get('job_id'):
        return JsonResponse({'error': 'AI service submission failed'}, status=500)
    
    # Create inspection records for each file
    inspections = []
    for file in files:
        inspection = Inspection.objects.create(
            name=file.name,
            uploaded_by=request.user,
            job_id=result['job_id'],
            status='queued'
        )
        inspections.append({
            'id': str(inspection.id),
            'name': inspection.name,
            'status': inspection.status
        })
    
    return JsonResponse({
        'success': True,
        'job_id': result['job_id'],
        'file_count': result['file_count'],
        'message': result['message'],
        'status_check_url': result['status_check_url'],
        'inspections': inspections
    })


@login_required
def check_job_status(request, job_id):
    """
    Check status of a job
    """
    ai_client = AIServiceClient()
    status = ai_client.check_status(job_id)
    
    if status:
        return JsonResponse(status)
    
    return JsonResponse({'error': 'Job not found'}, status=404)


@login_required
def inspection_detail(request, pk):
    """
    Show detailed view of an inspection
    """
    inspection = get_object_or_404(Inspection, pk=pk, uploaded_by=request.user)
    
    # If still queued/processing, try to fetch results
    if inspection.status in ['queued', 'processing'] and inspection.job_id:
        ai_client = AIServiceClient()
        results = ai_client.get_results_from_s3(
            str(inspection.job_id),
            inspection.name
        )
        
        if results:
            # Update inspection with results
            inspection.status = 'completed'
            inspection.ai_classification = results.get('prediction')
            inspection.ai_confidence = results.get('confidence')
            inspection.ai_processed_at = results.get('processed_at')
            
            # Store defects in a JSON field or as a text field
            # Since you removed the Defect model, you might want to add a defects_data JSONField to your Inspection model
            # For now, we'll just save the explanation if available
            if results.get('defects'):
                import json
                inspection.ai_explanation = json.dumps(results.get('defects'))
            
            inspection.save()
    
    # Check if there's a human override
    try:
        override = inspection.override
    except HumanOverride.DoesNotExist:
        override = None
    
    context = {
        'inspection': inspection,
        'override': override,
        # If you have defects stored in ai_explanation as JSON, you can parse it
        'defects': []  # You can populate this if needed
    }
    
    # If you stored defects in ai_explanation as JSON, parse it
    if inspection.ai_explanation:
        try:
            import json
            context['defects'] = json.loads(inspection.ai_explanation)
        except:
            pass
    
    return render(request, 'inspections/detail.html', context)


@login_required
def inspection_list(request):
    """
    List all inspections with pagination and filters
    """
    # Filter by current user only
    inspections = Inspection.objects.filter(uploaded_by=request.user)
    
    # Add search filter
    search = request.GET.get('search')
    if search:
        inspections = inspections.filter(name__icontains=search)
    
    # Add status filter
    status = request.GET.get('status')
    if status:
        inspections = inspections.filter(status=status)
    
    # Add date filter (filter by date uploaded)
    date_filter = request.GET.get('date')
    if date_filter:
        inspections = inspections.filter(uploaded_at__date=date_filter)
    
    # Order by most recent first
    inspections = inspections.order_by('-uploaded_at')
    
    # Pagination - 10 items per page
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
        'status_choices': Inspection.STATUS_CHOICES,
    }
    return render(request, 'inspections/list.html', context)

@login_required
def analytics_dashboard(request):
    """Analytics and insights dashboard"""
    
    # Get statistics for the dashboard
    total_inspections = Inspection.objects.filter(uploaded_by=request.user).count()
    
    # Good vs Defective counts
    good_count = Inspection.objects.filter(
        uploaded_by=request.user,
        ai_classification='good'
    ).count()
    
    defective_count = Inspection.objects.filter(
        uploaded_by=request.user,
        ai_classification='defect'
    ).count()
    
    # Human override count
    override_count = Inspection.objects.filter(
        uploaded_by=request.user,
        human_override=True
    ).count()
    
    # Calculate percentages
    good_percentage = (good_count / total_inspections * 100) if total_inspections > 0 else 0
    defective_percentage = (defective_count / total_inspections * 100) if total_inspections > 0 else 0
    override_percentage = (override_count / total_inspections * 100) if total_inspections > 0 else 0
    
    # Get recent trend data (last 7 days)
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



@login_required
@require_POST
def human_override(request, pk):
    """
    Handle human override of AI results - creates or updates override
    """
    import json
    from django.utils import timezone
    
    inspection = get_object_or_404(Inspection, pk=pk, uploaded_by=request.user)
    
    # Get data from POST
    classification = request.POST.get('classification')
    reason = request.POST.get('reason')
    notes = request.POST.get('notes', '')
    
    if not classification or not reason:
        return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
    
    from .models import HumanOverride
    
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
        override.to_date = request.POST.get('to_date') if request.POST.get('to_date') else None
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
            to_date=request.POST.get('to_date') if request.POST.get('to_date') else None
        )
    
    # Update inspection
    inspection.human_override = True
    inspection.status = 'completed'
    inspection.ai_classification = classification
    inspection.save()
    
    return JsonResponse({
        'success': True, 
        'message': 'Override saved successfully',
        'is_update': True if 'override' in locals() and override.id else False,
        'override_id': str(override.id)
    })

@login_required
def review_queue(request):
    """
    Display all inspections that need human review
    Status can be: 'human_review'.
    You can customize which statuses appear here
    """
    # Get inspections that need review
    # You can modify this query based on your needs
    review_inspections = Inspection.objects.filter(
        uploaded_by=request.user,
        status__in=['human_review']  # Add statuses that need review
    ).order_by('-uploaded_at')
    
    # Count for badge
    review_count = review_inspections.count()
    
    context = {
        'inspections': review_inspections,
        'review_count': review_count,
        'status_choices': Inspection.STATUS_CHOICES,
    }
    return render(request, 'inspections/review_queue.html', context)

@login_required
@require_POST
def update_inspection_status(request, pk):
    """
    API endpoint to update inspection status from review queue
    """
    inspection = get_object_or_404(Inspection, pk=pk, uploaded_by=request.user)
    
    new_status = request.POST.get('status')
    notes = request.POST.get('notes', '')
    
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

# Also add a context processor to show count in sidebar
def review_queue_count(request):
    """
    Context processor to show count in sidebar badge
    Add this to TEMPLATES context_processors in settings.py
    """
    if request.user.is_authenticated:
        count = Inspection.objects.filter(
            uploaded_by=request.user,
            status__in=['human_review']
        ).count()
        return {'review_queue_count': count}
    return {'review_queue_count': 0}