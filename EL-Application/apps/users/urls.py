from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    
    # User Management (Admin only)
    path('', views.user_list_view, name='user_list'),
    path('create/', views.user_create_view, name='user_create'),
    path('<int:user_id>/update/', views.user_update_view, name='user_update'),
    path('<int:user_id>/delete/', views.user_delete_view, name='user_delete'),
    path('<int:user_id>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    path('<int:user_id>/reset-deactivation/', views.user_reset_deactivation, name='user_reset_deactivation'),
]