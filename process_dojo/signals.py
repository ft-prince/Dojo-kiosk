"""
Process DOJO - Django Signals
Automatic tracking of login/logout sessions and user profile management
"""
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import LoginSession, EmployeeProfile


@receiver(user_logged_in)
def create_login_session(sender, request, user, **kwargs):
    """Create a new login session when user logs in"""
    LoginSession.objects.create(
        user=user,
        login_time=timezone.now()
    )


@receiver(user_logged_out)
def close_login_session(sender, request, user, **kwargs):
    """Close the most recent login session when user logs out"""
    if user:
        # Get the most recent open session (no logout time)
        open_session = LoginSession.objects.filter(
            user=user,
            logout_time__isnull=True
        ).order_by('-login_time').first()
        
        if open_session:
            open_session.logout_time = timezone.now()
            open_session.calculate_duration()


@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    """
    Optionally create an employee profile when a new user is created.
    This can be disabled if profiles are created through a different process.
    """
    if created:
        # Only create if it doesn't exist
        if not hasattr(instance, 'employee_profile'):
            # You may want to disable this auto-creation in production
            # and create profiles manually with proper employee details
            pass