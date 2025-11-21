"""
Process DOJO - Biometric Authentication Views
SecuGen fingerprint integration for employee login
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
import json
import base64

from .models import EmployeeProfile, LoginSession
from .biometric_service import BiometricService


# ============================================================================
# BIOMETRIC LOGIN
# ============================================================================

def biometric_login_view(request):
    """
    Biometric login page with fingerprint scanner interface
    """
    if request.user.is_authenticated:
        return redirect('process_dojo:dashboard')
    
    context = {
        'page_title': 'Biometric Login',
        'total_employees': EmployeeProfile.objects.filter(
            biometric_id__isnull=False
        ).count(),
    }
    return render(request, 'biometric/biometric_login.html', context)


@csrf_exempt
@require_POST
def biometric_authenticate(request):
    """
    API endpoint to authenticate user via fingerprint
    Expected JSON: {
        "template": "base64_encoded_fingerprint_template"
    }
    """
    try:
        data = json.loads(request.body)
        template_b64 = data.get('template')
        
        if not template_b64:
            return JsonResponse({
                'success': False,
                'error': 'No fingerprint template provided'
            }, status=400)
        
        # Decode the template
        template_bytes = base64.b64decode(template_b64)
        
        # Initialize biometric service
        bio_service = BiometricService()
        
        # Match against all enrolled fingerprints
        match_result = bio_service.identify_user(template_bytes)
        
        if match_result['success'] and match_result['user']:
            user = match_result['user']
            
            # Create login session
            login_session = LoginSession.objects.create(
                user=user,
                login_time=timezone.now()
            )
            
            # Log the user in
            login(request, user)
            
            # Store session ID for later logout tracking
            request.session['login_session_id'] = login_session.id
            
            return JsonResponse({
                'success': True,
                'user': {
                    'username': user.username,
                    'full_name': user.get_full_name(),
                    'employee_id': user.employee_profile.employee_id,
                    'plant': user.employee_profile.plant,
                    'unit': user.employee_profile.unit,
                    'department': user.employee_profile.department,
                },
                'redirect_url': ''
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Fingerprint not recognized. Please try again.'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Authentication error: {str(e)}'
        }, status=500)


def biometric_logout_view(request):
    """
    Logout and track session duration
    """
    if request.user.is_authenticated:
        # Update logout time for session
        session_id = request.session.get('login_session_id')
        if session_id:
            try:
                login_session = LoginSession.objects.get(id=session_id)
                login_session.logout_time = timezone.now()
                login_session.calculate_duration()
            except LoginSession.DoesNotExist:
                pass
        
        logout(request)
    
    return redirect('process_dojo:biometric_login')


# ============================================================================
# BIOMETRIC ENROLLMENT (Admin Only)
# ============================================================================

@login_required
@user_passes_test(lambda u: u.is_staff)
def biometric_enrollment_list(request):
    """
    List all employees with enrollment status
    """
    employees = EmployeeProfile.objects.select_related('user').all()
    
    enrolled_count = employees.filter(biometric_id__isnull=False).count()
    pending_count = employees.filter(biometric_id__isnull=True).count()
    
    # Get unique plants for filter
    unique_plants = employees.values_list('plant', flat=True).distinct().order_by('plant')
    
    context = {
        'page_title': 'Biometric Enrollment',
        'employees': employees,
        'enrolled_count': enrolled_count,
        'pending_count': pending_count,
        'unique_plants': unique_plants,
    }
    return render(request, 'biometric/biometric_enrollment_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def biometric_enrollment_form(request, employee_id):
    """
    Enrollment form for capturing fingerprint
    """
    profile = get_object_or_404(EmployeeProfile, employee_id=employee_id)
    
    # Get stored image if exists
    stored_image_url = None
    if profile.biometric_id:
        # Check if PNG exists
        from django.conf import settings
        from pathlib import Path
        data_dir = Path(settings.MEDIA_ROOT) / 'biometric_data'
        png_path = data_dir / f"{profile.biometric_id}.png"
        if png_path.exists():
            stored_image_url = f"/media/biometric_data/{profile.biometric_id}.png"
    
    context = {
        'page_title': f'Enroll Fingerprint - {profile.user.get_full_name()}',
        'profile': profile,
        'is_reenrollment': bool(profile.biometric_id),
        'stored_image_url': stored_image_url,
    }
    return render(request, 'biometric/biometric_enrollment_form.html', context)


@csrf_exempt
@require_POST
@login_required
@user_passes_test(lambda u: u.is_staff)
def biometric_enroll_save(request):
    """
    Save enrolled fingerprint template
    Expected JSON: {
        "employee_id": "EMP001",
        "template": "base64_encoded_template",
        "image": "base64_encoded_image",
        "quality": 85
    }
    """
    try:
        data = json.loads(request.body)
        employee_id = data.get('employee_id')
        template_b64 = data.get('template')
        image_b64 = data.get('image')
        quality = data.get('quality', 0)
        
        if not all([employee_id, template_b64]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)
        
        profile = get_object_or_404(EmployeeProfile, employee_id=employee_id)
        
        # Initialize biometric service
        bio_service = BiometricService()
        
        # Save the fingerprint
        result = bio_service.enroll_user(
            user=profile.user,
            template_b64=template_b64,
            image_b64=image_b64
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f'Fingerprint enrolled successfully for {profile.user.get_full_name()}',
                'biometric_id': result['biometric_id']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=400)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Enrollment error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_POST
@login_required
@user_passes_test(lambda u: u.is_staff)
def biometric_delete(request):
    """
    Delete enrolled fingerprint
    Expected JSON: {
        "employee_id": "EMP001"
    }
    """
    try:
        data = json.loads(request.body)
        employee_id = data.get('employee_id')
        
        if not employee_id:
            return JsonResponse({
                'success': False,
                'error': 'Employee ID required'
            }, status=400)
        
        profile = get_object_or_404(EmployeeProfile, employee_id=employee_id)
        
        # Initialize biometric service
        bio_service = BiometricService()
        
        # Delete the fingerprint
        result = bio_service.delete_user_fingerprint(profile.user)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f'Fingerprint deleted for {profile.user.get_full_name()}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['error']
            })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Delete error: {str(e)}'
        }, status=500)


# ============================================================================
# BIOMETRIC HEALTH CHECK
# ============================================================================

@csrf_exempt
def biometric_device_status(request):
    """
    Check if biometric device is connected and ready
    """
    try:
        bio_service = BiometricService()
        status = bio_service.get_device_status()
        
        return JsonResponse({
            'success': True,
            'device_connected': status['connected'],
            'device_info': status.get('info', {}),
            'enrolled_count': EmployeeProfile.objects.filter(
                biometric_id__isnull=False
            ).count()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'device_connected': False
        })