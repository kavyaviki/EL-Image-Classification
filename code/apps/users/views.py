from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from .models import User
from .forms import CustomUserCreationForm, CustomUserChangeForm, LoginForm

# Authentication Views
def register_view(request):
    """
    User registration view
    """
    if request.method == 'POST':
        # ===== FORM SUBMISSION FLOW =====
        # Create form instance with POST data
        form = CustomUserCreationForm(request.POST)
        # Validate the form data
        if form.is_valid():
            # ===== SUCCESS PATH =====
            # Save user to database
            user = form.save()
            # Log the user in (create session)
            login(request, user) # This creates session cookie  
            # Success message (stored in session)
            messages.success(request, f"Account created successfully! Welcome {user.username}!")
            # Redirect to profile page
            return redirect('users:profile')
        else:
            # ===== ERROR PATH =====
            # Form has errors, show them
            messages.error(request, "Please correct the errors below.")
            # Falls through to render template with errors
    else:
        # ===== GET REQUEST FLOW (Initial page load) =====
        # Create empty form instance
        form = CustomUserCreationForm()
    # ===== RENDER TEMPLATE =====
    # This runs for:
    # - GET requests (initial page load)
    # - POST with invalid data (show errors)
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    """
    User login view
    """
    if request.user.is_authenticated:
        return redirect('users:profile')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if user:
                login(request, user)
                messages.success(request, f"Welcome back {user.username}!")
                next_url = request.GET.get('next', 'inspections:upload')
                return redirect(next_url)
    else:
        form = LoginForm()
    
    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    """
    User logout view
    """
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('users:login')


# Profile Views
@login_required
def profile_view(request):
    """
    View user profile
    """
    return render(request, 'users/profile.html', {'user': request.user})

@login_required
def profile_edit_view(request):
    """
    Edit user profile
    """
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('users:profile')
    else:
        form = CustomUserChangeForm(instance=request.user)
    
    return render(request, 'users/profile_edit.html', {'form': form})


# Admin User Management Views
@login_required
def user_list_view(request):
    """
    List all users (admin only)
    """
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to view this page.")
        return redirect('users:profile')
    
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) | 
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).order_by('-date_joined')
    else:
        users = User.objects.all().order_by('-date_joined')
    
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'users/user_list.html', {'page_obj': page_obj, 'query': query})

@login_required
def user_create_view(request):
    """
    Create a new user (admin only)
    """
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('users:profile')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User {user.username} created successfully!")
            return redirect('users:user_list')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/user_form.html', {'form': form, 'action': 'Create'})

@login_required
def user_update_view(request, user_id):
    """
    Update a user (admin only)
    """
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('users:profile')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"User {user.username} updated successfully!")
            return redirect('users:user_list')
    else:
        form = CustomUserChangeForm(instance=user)
    
    return render(request, 'users/user_form.html', {'form': form, 'action': 'Update', 'user': user})

@login_required
def user_delete_view(request, user_id):
    """
    Delete a user (admin only)
    """
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('users:profile')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"User {username} deleted successfully!")
        return redirect('users:user_list')
    
    return render(request, 'users/user_confirm_delete.html', {'user': user})