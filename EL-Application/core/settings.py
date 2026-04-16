"""
Django settings for core project.
"""

from pathlib import Path
import os
from decouple import config

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Increase maximum number of files that can be uploaded
DATA_UPLOAD_MAX_NUMBER_FILES = None

# SECURITY
SECRET_KEY = 'django-insecure-92hs_v06+e6bx=4gp&q_(#%b1!mzdw97zjod72l*xc_#&_j@mw'

# ⚠️ Set False in production
DEBUG = True

ALLOWED_HOSTS = [
    "ec2-13-203-137-15.ap-south-1.compute.amazonaws.com",
    "https://pv-scan.viki.ai/",
    "13.203.137.15",
    "localhost",
    "127.0.0.1"
]


# APPLICATIONS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'crispy_forms',
    'crispy_bootstrap5',

    # Your apps
    'apps.users',
    'apps.inspections',
]


# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    # ✅ WhiteNoise for static files (IMPORTANT)
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'core.urls'


# TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Cross-platform
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'core.wsgi.application'


# DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}


# PASSWORD VALIDATION
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# INTERNATIONALIZATION
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ==============================
# STATIC FILES (FIXED)
# ==============================

STATIC_URL = '/static/'

# Source static files (your development files)
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Collected static files (used in production)
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise storage (compression + cache)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ==============================
# MEDIA FILES
# ==============================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ==============================
# CUSTOM USER MODEL
# ==============================

AUTH_USER_MODEL = 'users.User'


# ==============================
# CRISPY FORMS
# ==============================

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# ==============================
# AUTH REDIRECTS
# ==============================

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'inspections:upload'
LOGOUT_REDIRECT_URL = 'users:login'


# ==============================
# AI SERVICE
# ==============================

AI_SERVICE_URL = config('AI_SERVICE_URL', default='http://localhost:8001')


# ==============================
# AWS CONFIG
# ==============================

AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = config('S3_BUCKET', default='')
AWS_S3_REGION = config('AWS_REGION', default='ap-south-1')


# ==============================
# BUSINESS LOGIC CONFIG
# ==============================

REVIEW_CONFIDENCE_THRESHOLD = config('REVIEW_CONFIDENCE_THRESHOLD', default='0.8')

AUTO_DEACTIVATE_USERS = config('AUTO_DEACTIVATE_USERS', default=False, cast=bool)
AUTO_DEACTIVATE_DAYS = config('AUTO_DEACTIVATE_DAYS', default=30, cast=int)
AUTO_DEACTIVATE_ADMINS = config('AUTO_DEACTIVATE_ADMINS', default=False, cast=bool)


# ==============================
# DEFAULT AUTO FIELD
# ==============================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'