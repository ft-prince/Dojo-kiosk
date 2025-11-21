"""
SecuGen SDK Wrapper for Django Integration
Simplified version focused on core fingerprint operations
"""
import ctypes
from ctypes import wintypes
import os

# SecuGen SDK Constants
SGFDX_ERROR_NONE = 0
SG_DEV_AUTO = 0x00FF


class SGDeviceInfoParam(ctypes.Structure):
    _fields_ = [
        ("DeviceID", wintypes.DWORD),
        ("DeviceSN", ctypes.c_char * 16),
        ("ComPort", wintypes.DWORD),
        ("ComSpeed", wintypes.DWORD),
        ("ImageWidth", wintypes.DWORD),
        ("ImageHeight", wintypes.DWORD),
        ("Contrast", wintypes.DWORD),
        ("Brightness", wintypes.DWORD),
        ("Gain", wintypes.DWORD),
        ("ImageDPI", wintypes.DWORD),
        ("FWVersion", wintypes.DWORD)
    ]


class SGFingerInfo(ctypes.Structure):
    _fields_ = [
        ("FingerNumber", wintypes.DWORD),
        ("ViewNumber", wintypes.DWORD),
        ("ImpressionType", wintypes.DWORD),
        ("ImageQuality", wintypes.DWORD)
    ]


class SecuGenSDK:
    """
    Wrapper for SecuGen FDx SDK Pro
    Core operations for fingerprint capture and matching
    """
    
    def __init__(self, dll_path=None):
        self.dll = None
        self.h_device = None
        self.image_width = 260
        self.image_height = 300
        self.dll_path = dll_path
    
    def load_library(self):
        """Load the SecuGen DLL"""
        if not self.dll_path or not os.path.exists(self.dll_path):
            return False, f"DLL not found: {self.dll_path}"
        try:
            self.dll = ctypes.WinDLL(self.dll_path)
            return True, "OK"
        except Exception as e:
            return False, str(e)
    
    def create_object(self):
        """Create SDK object handle"""
        try:
            self.dll.SGFPM_Create.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
            self.dll.SGFPM_Create.restype = wintypes.DWORD
            self.h_device = ctypes.c_void_p()
            result = self.dll.SGFPM_Create(ctypes.byref(self.h_device))
            return result == SGFDX_ERROR_NONE, f"Error: {result}" if result else "OK"
        except Exception as e:
            return False, str(e)
    
    def init_device(self, device_id=SG_DEV_AUTO):
        """Initialize the fingerprint device"""
        try:
            self.dll.SGFPM_Init.argtypes = [ctypes.c_void_p, wintypes.DWORD]
            self.dll.SGFPM_Init.restype = wintypes.DWORD
            result = self.dll.SGFPM_Init(self.h_device, device_id)
            return result == SGFDX_ERROR_NONE, f"Error: {result}" if result else "OK"
        except Exception as e:
            return False, str(e)
    
    def open_device(self, port=0):
        """Open connection to the device"""
        try:
            self.dll.SGFPM_OpenDevice.argtypes = [ctypes.c_void_p, wintypes.DWORD]
            self.dll.SGFPM_OpenDevice.restype = wintypes.DWORD
            result = self.dll.SGFPM_OpenDevice(self.h_device, port)
            if result == SGFDX_ERROR_NONE:
                self._get_device_info()
                return True, "OK"
            return False, f"Error: {result}"
        except Exception as e:
            return False, str(e)
    
    def _get_device_info(self):
        """Get device information (width, height, etc.)"""
        try:
            self.dll.SGFPM_GetDeviceInfo.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(SGDeviceInfoParam)
            ]
            self.dll.SGFPM_GetDeviceInfo.restype = wintypes.DWORD
            info = SGDeviceInfoParam()
            if self.dll.SGFPM_GetDeviceInfo(self.h_device, ctypes.byref(info)) == SGFDX_ERROR_NONE:
                self.image_width = info.ImageWidth
                self.image_height = info.ImageHeight
        except:
            pass
    
    def close_device(self):
        """Close device connection"""
        if self.dll and self.h_device:
            try:
                self.dll.SGFPM_CloseDevice.argtypes = [ctypes.c_void_p]
                self.dll.SGFPM_CloseDevice(self.h_device)
            except:
                pass
    
    def get_image(self):
        """Capture fingerprint image from device"""
        try:
            buf_size = self.image_width * self.image_height
            img_buf = (ctypes.c_ubyte * buf_size)()
            self.dll.SGFPM_GetImage.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_ubyte)
            ]
            self.dll.SGFPM_GetImage.restype = wintypes.DWORD
            result = self.dll.SGFPM_GetImage(self.h_device, img_buf)
            if result == SGFDX_ERROR_NONE:
                return True, bytes(img_buf)
            return False, f"Error: {result}"
        except Exception as e:
            return False, str(e)
    
    def get_image_quality(self, image_data):
        """Get quality score of fingerprint image"""
        try:
            quality = wintypes.DWORD()
            img_buf = (ctypes.c_ubyte * len(image_data))(*image_data)
            self.dll.SGFPM_GetImageQuality.argtypes = [
                ctypes.c_void_p,
                wintypes.DWORD,
                wintypes.DWORD,
                ctypes.POINTER(ctypes.c_ubyte),
                ctypes.POINTER(wintypes.DWORD)
            ]
            self.dll.SGFPM_GetImageQuality.restype = wintypes.DWORD
            if self.dll.SGFPM_GetImageQuality(
                self.h_device,
                self.image_width,
                self.image_height,
                img_buf,
                ctypes.byref(quality)
            ) == SGFDX_ERROR_NONE:
                return quality.value
        except:
            pass
        return 0
    
    def create_template(self, image_data):
        """Create fingerprint template from image"""
        try:
            # Get max template size
            self.dll.SGFPM_GetMaxTemplateSize.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(wintypes.DWORD)
            ]
            self.dll.SGFPM_GetMaxTemplateSize.restype = wintypes.DWORD
            max_size = wintypes.DWORD()
            self.dll.SGFPM_GetMaxTemplateSize(self.h_device, ctypes.byref(max_size))
            
            # Create template buffer
            tmpl_buf = (ctypes.c_ubyte * max_size.value)()
            img_buf = (ctypes.c_ubyte * len(image_data))(*image_data)
            
            # Set finger info
            fi = SGFingerInfo()
            fi.FingerNumber = 1
            fi.ViewNumber = 1
            fi.ImpressionType = 0
            fi.ImageQuality = self.get_image_quality(image_data)
            
            # Create template
            self.dll.SGFPM_CreateTemplate.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(SGFingerInfo),
                ctypes.POINTER(ctypes.c_ubyte),
                ctypes.POINTER(ctypes.c_ubyte)
            ]
            self.dll.SGFPM_CreateTemplate.restype = wintypes.DWORD
            
            if self.dll.SGFPM_CreateTemplate(
                self.h_device,
                ctypes.byref(fi),
                img_buf,
                tmpl_buf
            ) == SGFDX_ERROR_NONE:
                # Get actual template size
                self.dll.SGFPM_GetTemplateSize.argtypes = [
                    ctypes.c_void_p,
                    ctypes.POINTER(ctypes.c_ubyte),
                    ctypes.POINTER(wintypes.DWORD)
                ]
                actual_size = wintypes.DWORD()
                self.dll.SGFPM_GetTemplateSize(
                    self.h_device,
                    tmpl_buf,
                    ctypes.byref(actual_size)
                )
                return True, bytes(tmpl_buf[:actual_size.value])
            return False, "Template creation failed"
        except Exception as e:
            return False, str(e)
    
    def match_templates(self, template1, template2, security_level=5):
        """
        Match two fingerprint templates
        
        Args:
            template1: First template bytes
            template2: Second template bytes
            security_level: Matching security level (1-9, default 5)
        
        Returns:
            (success: bool, matched: bool)
        """
        try:
            if not self.h_device:
                print("[ERROR] Device handle not initialized for matching")
                return False, False
            
            t1_buf = (ctypes.c_ubyte * len(template1))(*template1)
            t2_buf = (ctypes.c_ubyte * len(template2))(*template2)
            matched = ctypes.c_bool()
            
            self.dll.SGFPM_MatchTemplate.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_ubyte),
                ctypes.POINTER(ctypes.c_ubyte),
                wintypes.DWORD,
                ctypes.POINTER(ctypes.c_bool)
            ]
            self.dll.SGFPM_MatchTemplate.restype = wintypes.DWORD
            
            result = self.dll.SGFPM_MatchTemplate(
                self.h_device,
                t1_buf,
                t2_buf,
                security_level,
                ctypes.byref(matched)
            )
            
            if result == SGFDX_ERROR_NONE:
                return True, matched.value
            else:
                print(f"[ERROR] SGFPM_MatchTemplate failed with code: {result}")
                return False, False
                
        except Exception as e:
            print(f"[ERROR] Match error: {e}")
            import traceback
            traceback.print_exc()
            return False, False
    
    def destroy(self):
        """Terminate SDK and release resources"""
        if self.dll and self.h_device:
            try:
                self.dll.SGFPM_Terminate.argtypes = [ctypes.c_void_p]
                self.dll.SGFPM_Terminate(self.h_device)
            except:
                pass