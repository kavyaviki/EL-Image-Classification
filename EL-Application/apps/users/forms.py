from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import authenticate
from .models import User

class CustomUserCreationForm(UserCreationForm):
    """
    Form for creating new users
    """
    # Define form fields with widgets (HTML controls)
    email = forms.EmailField(
        required=True, # Field is mandator
        widget=forms.EmailInput(attrs={ # HTML input type=email
            'class': 'form-control',    # Bootstrap CSS class
            'placeholder': 'Email'})    # Placeholder text
    )
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    )
    
    class Meta:
        model = User # Which model this form saves to
        fields = ('username', 'email', 'password1', 'password2') # This tells Django which fields to include
    
    def clean_email(self):
        """
        Custom validation for email field
        Called automatically by form.is_valid()
        """
        email = self.cleaned_data.get('email')
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email
    
    def save(self, commit=True):
        # Create user object but don't save ye
        user = super().save(commit=False)
        # Set email from cleaned data
        user.email = self.cleaned_data['email']
        # Save to database if commit=True
        if commit:
            user.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    """
    Form for updating users
    """
    password = None  # Hide password field
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 
                 'phone_number', 'profile_picture')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

class LoginForm(forms.Form):
    """
    Form for user login
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        if email and password:
            # Try to authenticate with email as username (since USERNAME_FIELD is email)
            self.user = authenticate(username=email, password=password)
            
            if self.user is None:
                raise forms.ValidationError("Invalid email or password.")
            
            # Check if user is active
            if not self.user.is_active:
                raise forms.ValidationError("This account is inactive.")
        
        return self.cleaned_data
    
    def get_user(self):
        return getattr(self, 'user', None)