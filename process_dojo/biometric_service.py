"""
Process DOJO - Biometric Service
Bridge between SecuGen SDK and Django application
"""
import os
import json
import base64
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

# Import the SecuGen SDK wrapper
import sys
sdk_path = os.path.join(settings.BASE_DIR, 'biometric_sdk')
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

try:
    from secugen_wrapper import SecuGenSDK
except ImportError:
    SecuGenSDK = None


class BiometricDatabase:
    """
    Django-integrated fingerprint database
    Stores templates in database via EmployeeProfile.biometric_id
    """
    
    def __init__(self):
        # Path to store fingerprint templates and images
        self.data_dir = Path(settings.MEDIA_ROOT) / 'biometric_data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def save_fingerprint(self, user: User, template: bytes, image: Optional[bytes] = None) -> str:
        """
        Save fingerprint template and image for a user
        Returns biometric_id (UUID-like string)
        """
        from .models import EmployeeProfile
        from PIL import Image
        import io
        
        # Generate unique biometric ID
        biometric_id = f"BIO_{user.id}_{user.username}"
        
        # Save template file
        template_path = self.data_dir / f"{biometric_id}.template"
        with open(template_path, 'wb') as f:
            f.write(template)
        
        # Save image file if provided - convert to PNG for proper viewing
        if image:
            try:
                # Log image info for debugging
                print(f"[DEBUG] Image bytes length: {len(image)}")
                
                # Calculate expected size for common SecuGen dimensions
                expected_260x300 = 260 * 300  # 78000 bytes
                expected_300x400 = 300 * 400  # 120000 bytes
                
                # Determine image dimensions based on byte count
                if len(image) == expected_260x300:
                    width, height = 260, 300
                    print(f"[DEBUG] Detected 260x300 image")
                elif len(image) == expected_300x400:
                    width, height = 300, 400
                    print(f"[DEBUG] Detected 300x400 image")
                else:
                    # Try to detect from common SecuGen sizes
                    # Most common: 260x300, 300x400, 320x400
                    possible_dims = [
                        (260, 300),
                        (300, 400),
                        (320, 400),
                        (256, 256),
                    ]
                    
                    width, height = None, None
                    for w, h in possible_dims:
                        if w * h == len(image):
                            width, height = w, h
                            print(f"[DEBUG] Matched dimensions: {w}x{h}")
                            break
                    
                    if not width:
                        # Default to 260x300 and pad/trim
                        width, height = 260, 300
                        expected_size = width * height
                        if len(image) < expected_size:
                            # Pad with zeros
                            image = image + bytes(expected_size - len(image))
                            print(f"[WARN] Image padded from {len(image)} to {expected_size} bytes")
                        elif len(image) > expected_size:
                            # Trim
                            image = image[:expected_size]
                            print(f"[WARN] Image trimmed from {len(image)} to {expected_size} bytes")
                
                # Create PIL Image from grayscale bytes
                img = Image.frombytes('L', (width, height), image)
                
                # Save as PNG
                image_path = self.data_dir / f"{biometric_id}.png"
                img.save(image_path, 'PNG')
                print(f"[INFO] Saved fingerprint image: {image_path} ({width}x{height})")
                
            except Exception as e:
                print(f"[ERROR] Image save failed: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback: save raw bytes
                image_path = self.data_dir / f"{biometric_id}.img"
                with open(image_path, 'wb') as f:
                    f.write(image)
                print(f"[WARN] Saved as raw bytes: {image_path}")
        
        # Update employee profile
        try:
            profile = user.employee_profile
            profile.biometric_id = biometric_id
            profile.save(update_fields=['biometric_id'])
        except EmployeeProfile.DoesNotExist:
            raise ValueError(f"No employee profile found for user {user.username}")
        
        return biometric_id
    
    def get_template(self, biometric_id: str) -> Optional[bytes]:
        """
        Retrieve fingerprint template by biometric_id
        """
        template_path = self.data_dir / f"{biometric_id}.template"
        if template_path.exists():
            with open(template_path, 'rb') as f:
                return f.read()
        return None
    
    def get_image(self, biometric_id: str) -> Optional[bytes]:
        """
        Retrieve fingerprint image by biometric_id
        """
        # Try PNG first (new format)
        image_path = self.data_dir / f"{biometric_id}.png"
        if image_path.exists():
            with open(image_path, 'rb') as f:
                return f.read()
        
        # Fallback to raw format (old format)
        image_path = self.data_dir / f"{biometric_id}.img"
        if image_path.exists():
            with open(image_path, 'rb') as f:
                return f.read()
        
        return None
    
    def get_all_enrolled_users(self):
        """
        Get all users with enrolled fingerprints
        Returns list of (User, biometric_id) tuples
        """
        from .models import EmployeeProfile
        
        profiles = EmployeeProfile.objects.filter(
            biometric_id__isnull=False
        ).select_related('user')
        
        result = []
        for profile in profiles:
            template_path = self.data_dir / f"{profile.biometric_id}.template"
            if template_path.exists():
                result.append((profile.user, profile.biometric_id))
        
        return result
    
    def delete_fingerprint(self, user: User) -> bool:
        """
        Delete fingerprint data for a user
        """
        from .models import EmployeeProfile
        
        try:
            profile = user.employee_profile
            if profile.biometric_id:
                # Delete files (both formats)
                template_path = self.data_dir / f"{profile.biometric_id}.template"
                image_path_png = self.data_dir / f"{profile.biometric_id}.png"
                image_path_img = self.data_dir / f"{profile.biometric_id}.img"
                
                template_path.unlink(missing_ok=True)
                image_path_png.unlink(missing_ok=True)
                image_path_img.unlink(missing_ok=True)
                
                # Clear biometric_id
                profile.biometric_id = None
                profile.save(update_fields=['biometric_id'])
                return True
        except EmployeeProfile.DoesNotExist:
            pass
        
        return False


class BiometricService:
    """
    High-level biometric service for Django integration
    """
    
    def __init__(self):
        self.sdk = None
        self.db = BiometricDatabase()
        self._initialize_sdk()
    
    def _initialize_sdk(self):
        """
        Initialize SecuGen SDK for template matching
        Note: We don't need device access for matching, only for capture
        """
        if SecuGenSDK is None:
            print("[WARN] SecuGen SDK module not available")
            return
        
        try:
            # Look for DLL in configured path
            dll_path = getattr(settings, 'SECUGEN_DLL_PATH', None)
            if not dll_path:
                # Try default paths
                possible_paths = [
                    os.path.join(settings.BASE_DIR, 'biometric_sdk', 'sgfplib.dll'),
                    os.path.join(settings.BASE_DIR, 'biometric_sdk', 'bin', 'x64', 'sgfplib.dll'),
                    r'C:\SecuGen\sgfplib.dll',
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        dll_path = path
                        break
            
            if dll_path and os.path.exists(dll_path):
                print(f"[INFO] Loading SDK from: {dll_path}")
                self.sdk = SecuGenSDK(dll_path=dll_path)
                
                success, msg = self.sdk.load_library()
                if not success:
                    print(f"[ERROR] Failed to load library: {msg}")
                    self.sdk = None
                    return
                
                print(f"[INFO] Library loaded successfully")
                
                success, msg = self.sdk.create_object()
                if not success:
                    print(f"[ERROR] Failed to create object: {msg}")
                    self.sdk = None
                    return
                    
                print(f"[INFO] SDK object created successfully")
                
                # For matching, we don't need to init/open device
                # Those are only needed for capturing
                
            else:
                print(f"[ERROR] DLL not found at: {dll_path}")
        except Exception as e:
            print(f"[ERROR] SDK initialization failed: {e}")
            import traceback
            traceback.print_exc()
            self.sdk = None
    
    def get_device_status(self) -> Dict[str, Any]:
        """
        Check device connection status
        """
        if not self.sdk:
            return {
                'connected': False,
                'error': 'SDK not initialized'
            }
        
        try:
            success, msg = self.sdk.init_device()
            if not success:
                return {
                    'connected': False,
                    'error': msg
                }
            
            success, msg = self.sdk.open_device(0)
            if success:
                return {
                    'connected': True,
                    'info': {
                        'width': self.sdk.image_width,
                        'height': self.sdk.image_height
                    }
                }
            else:
                return {
                    'connected': False,
                    'error': msg
                }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def enroll_user(self, user: User, template_b64: str, image_b64: Optional[str] = None) -> Dict[str, Any]:
        """
        Enroll a user's fingerprint
        
        Args:
            user: Django User object
            template_b64: Base64-encoded fingerprint template
            image_b64: Optional base64-encoded fingerprint image
        
        Returns:
            Dict with success status and biometric_id or error
        """
        try:
            # Decode template
            template = base64.b64decode(template_b64)
            
            # Decode image if provided
            image = None
            if image_b64:
                image = base64.b64decode(image_b64)
            
            # Save to database
            biometric_id = self.db.save_fingerprint(user, template, image)
            
            return {
                'success': True,
                'biometric_id': biometric_id
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def identify_user(self, template: bytes) -> Dict[str, Any]:
        """
        Identify user by fingerprint template (1:N matching)
        Uses client bridge for matching since it has device access
        
        Args:
            template: Fingerprint template bytes
        
        Returns:
            Dict with success status and matched User or None
        """
        try:
            # Get all enrolled users
            enrolled_users = self.db.get_all_enrolled_users()
            
            print(f"[DEBUG] Identify: Checking {len(enrolled_users)} enrolled users")
            print(f"[DEBUG] Input template size: {len(template)} bytes")
            
            if not enrolled_users:
                return {
                    'success': False,
                    'user': None,
                    'error': 'No enrolled users found'
                }
            
            # Use client bridge for matching (it has device access)
            import requests
            template_b64 = base64.b64encode(template).decode('utf-8')
            
            # Match against each enrolled template via client bridge
            for user, biometric_id in enrolled_users:
                stored_template = self.db.get_template(biometric_id)
                if stored_template:
                    print(f"[DEBUG] Matching against {user.username} ({biometric_id})")
                    print(f"[DEBUG] Stored template size: {len(stored_template)} bytes")
                    
                    stored_template_b64 = base64.b64encode(stored_template).decode('utf-8')
                    
                    try:
                        # Call client bridge to do the matching
                        response = requests.post(
                            'http://localhost:5000/match',
                            json={
                                'template1': template_b64,
                                'template2': stored_template_b64
                            },
                            timeout=5
                        )
                        
                        if response.ok:
                            result = response.json()
                            success = result.get('success', False)
                            matched = result.get('matched', False)
                            
                            print(f"[DEBUG] Match result: success={success}, matched={matched}")
                            
                            if success and matched:
                                print(f"[DEBUG] ✓ MATCH FOUND: {user.username}")
                                return {
                                    'success': True,
                                    'user': user,
                                    'biometric_id': biometric_id
                                }
                        else:
                            print(f"[DEBUG] Client bridge error: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        print(f"[ERROR] Failed to connect to client bridge: {e}")
                        print(f"[ERROR] Make sure client bridge is running: python secugen_client_bridge.py")
                        return {
                            'success': False,
                            'user': None,
                            'error': 'Client bridge not accessible. Please start the client bridge.'
                        }
                else:
                    print(f"[DEBUG] No template found for {biometric_id}")
            
            print(f"[DEBUG] ✗ No match found after checking all users")
            return {
                'success': False,
                'user': None,
                'error': 'No match found'
            }
        except Exception as e:
            print(f"[DEBUG] Exception in identify_user: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'user': None,
                'error': str(e)
            }
    
    def verify_user(self, user: User, template: bytes) -> Dict[str, Any]:
        """
        Verify a specific user's fingerprint (1:1 matching)
        
        Args:
            user: Django User object
            template: Fingerprint template bytes to verify
        
        Returns:
            Dict with success status and matched boolean
        """
        if not self.sdk:
            return {
                'success': False,
                'matched': False,
                'error': 'SDK not initialized'
            }
        
        try:
            from .models import EmployeeProfile
            
            profile = user.employee_profile
            if not profile.biometric_id:
                return {
                    'success': False,
                    'matched': False,
                    'error': 'User has no enrolled fingerprint'
                }
            
            stored_template = self.db.get_template(profile.biometric_id)
            if not stored_template:
                return {
                    'success': False,
                    'matched': False,
                    'error': 'Fingerprint template not found'
                }
            
            success, matched = self.sdk.match_templates(template, stored_template)
            return {
                'success': success,
                'matched': matched
            }
        except EmployeeProfile.DoesNotExist:
            return {
                'success': False,
                'matched': False,
                'error': 'No employee profile found'
            }
        except Exception as e:
            return {
                'success': False,
                'matched': False,
                'error': str(e)
            }
    
    def delete_user_fingerprint(self, user: User) -> Dict[str, Any]:
        """
        Delete a user's enrolled fingerprint
        
        Args:
            user: Django User object
        
        Returns:
            Dict with success status
        """
        try:
            deleted = self.db.delete_fingerprint(user)
            if deleted:
                return {
                    'success': True,
                    'message': 'Fingerprint deleted successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'No fingerprint found to delete'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user_fingerprint_image(self, user: User) -> Optional[bytes]:
        """
        Get stored fingerprint image for a user
        
        Args:
            user: Django User object
        
        Returns:
            Image bytes or None
        """
        try:
            from .models import EmployeeProfile
            
            profile = user.employee_profile
            if profile.biometric_id:
                return self.db.get_image(profile.biometric_id)
        except EmployeeProfile.DoesNotExist:
            pass
        
        return None
    
    def cleanup(self):
        """
        Cleanup SDK resources
        """
        if self.sdk:
            try:
                self.sdk.close_device()
                self.sdk.destroy()
            except:
                pass