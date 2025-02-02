"""
Django settings for lhc_sharing project.

Generated by 'django-admin startproject' using Django 4.2.10.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import json
import os
from pathlib import Path

import environ
from google.oauth2 import service_account

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


env = environ.Env(DEBUG=(bool, False))
env_file = BASE_DIR / ".env"

if os.path.isfile(env_file):
    # Use a local secret file, if provided
    env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = ["localhost", ".vercel.app", "members-london.humanistchoir.org"]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "crispy_forms",
    "crispy_bootstrap5",
    "direct_cloud_upload",
    "invitations",
    "swingtime",
    "music",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "lhc_sharing.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "swingtime.context_processors.current_datetime",
            ],
        },
    },
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"


WSGI_APPLICATION = "lhc_sharing.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {"default": env.db()}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by email
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_ADAPTER = "invitations.models.InvitationsAdapter"
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = EMAIL_SUBJECT_PREFIX = "[London Humanist Choir] "
ACCOUNT_SIGNUP_FORM_CLASS = "music.forms.SignupForm"

INVITATIONS_ACCEPT_INVITE_AFTER_SIGNUP = True
INVITATIONS_ADAPTER = ACCOUNT_ADAPTER
INVITATIONS_INVITATION_EXPIRY = 7
INVITATIONS_INVITATION_ONLY = True

LOGIN_REDIRECT_URL = "home"

ADMINS = [("Chair", "chair@london.humanistchoir.org")]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = "static_root/static"
MEDIA_ROOT = "media/"
STATICFILES_DIRS = [BASE_DIR / "static"]

BUCKET_NAME = "london-humanist-choir"

if creds := env("GS_ACCOUNT_FILE"):
    GS_CREDENTIALS = service_account.Credentials.from_service_account_file(creds)
elif creds := env("GS_ACCOUNT_JSON"):
    GS_CREDENTIALS = service_account.Credentials.from_service_account_info(
        json.loads(creds)
    )


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DEFAULT_FROM_EMAIL = "LHC Members <chair@london.humanistchoir.org>"
EMAIL_BACKEND = "gmailapi_backend.mail.GmailBackend"
GMAIL_API_CLIENT_ID = env("GMAIL_API_CLIENT_ID")
GMAIL_API_CLIENT_SECRET = env("GMAIL_API_CLIENT_SECRET")
GMAIL_API_REFRESH_TOKEN = env("GMAIL_API_REFRESH_TOKEN")
