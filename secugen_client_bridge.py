"""
SecuGen Client Bridge for Django Web Integration
This application runs locally and provides HTTP API for web browser to communicate with SecuGen scanner
Run this on the kiosk machine: python secugen_client_bridge.py
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import sys
import os

# Import SecuGen SDK wrapper
from secugen_wrapper import SecuGenSDK

app = Flask(__name__)
CORS(app)  # Enable CORS for web browser access

# Global SDK instance
sdk = None
device_connected = False

# Minimum quality threshold
MIN_QUALITY = 50


def initialize_sdk():
    """Initialize SecuGen SDK"""
    global sdk, device_connected
    
    try:
        # Look for DLL in common locations
        possible_paths = [
            './sgfplib.dll',
            './bin/x64/sgfplib.dll',
            r'C:\SecuGen\sgfplib.dll',
        ]
        
        dll_path = None
        for path in possible_paths:
            if os.path.exists(path):
                dll_path = path
                break
        
        if not dll_path:
            print("ERROR: sgfplib.dll not found!")
            return False
        
        print(f"Using DLL: {dll_path}")
        sdk = SecuGenSDK(dll_path=dll_path)
        
        success, msg = sdk.load_library()
        if not success:
            print(f"ERROR: Failed to load library: {msg}")
            return False
        
        success, msg = sdk.create_object()
        if not success:
            print(f"ERROR: Failed to create object: {msg}")
            return False
        
        success, msg = sdk.init_device()
        if not success:
            print(f"ERROR: Failed to init device: {msg}")
            return False
        
        success, msg = sdk.open_device(0)
        if not success:
            print(f"ERROR: Failed to open device: {msg}")
            return False
        
        device_connected = True
        print(f"✓ Device connected: {sdk.image_width}x{sdk.image_height}")
        return True
        
    except Exception as e:
        print(f"ERROR: SDK initialization failed: {e}")
        return False


@app.route('/status', methods=['GET'])
def get_status():
    """Get device connection status"""
    return jsonify({
        'success': True,
        'connected': device_connected,
        'width': sdk.image_width if sdk else 0,
        'height': sdk.image_height if sdk else 0
    })


@app.route('/capture', methods=['POST'])
def capture_fingerprint():
    """
    Capture fingerprint image and create template
    Returns: {
        'success': bool,
        'image': base64_string,
        'template': base64_string,
        'quality': int
    }
    """
    if not device_connected or not sdk:
        return jsonify({
            'success': False,
            'error': 'Device not connected'
        }), 400
    
    try:
        # Capture image
        success, result = sdk.get_image()
        if not success:
            return jsonify({
                'success': False,
                'error': f'Capture failed: {result}'
            }), 400
        
        image_data = result
        
        # Get quality
        quality = sdk.get_image_quality(image_data)
        
        # Create template
        success, template = sdk.create_template(image_data)
        if not success:
            return jsonify({
                'success': False,
                'error': f'Template creation failed: {template}'
            }), 400
        
        # Encode to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        template_b64 = base64.b64encode(template).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': image_b64,
            'template': template_b64,
            'quality': quality,
            'width': sdk.image_width,
            'height': sdk.image_height
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/match', methods=['POST'])
def match_fingerprints():
    """
    Match two fingerprint templates
    Request: {
        'template1': base64_string,
        'template2': base64_string
    }
    Returns: {
        'success': bool,
        'matched': bool
    }
    """
    if not device_connected or not sdk:
        return jsonify({
            'success': False,
            'error': 'Device not connected'
        }), 400
    
    try:
        data = request.json
        template1_b64 = data.get('template1')
        template2_b64 = data.get('template2')
        
        if not template1_b64 or not template2_b64:
            return jsonify({
                'success': False,
                'error': 'Both templates required'
            }), 400
        
        # Decode templates
        template1 = base64.b64decode(template1_b64)
        template2 = base64.b64decode(template2_b64)
        
        # Match
        success, matched = sdk.match_templates(template1, template2)
        
        return jsonify({
            'success': success,
            'matched': matched
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/live-preview', methods=['GET'])
def live_preview():
    """
    Capture a single frame for live preview
    Returns: {
        'success': bool,
        'image': base64_string,
        'quality': int
    }
    """
    if not device_connected or not sdk:
        return jsonify({
            'success': False,
            'error': 'Device not connected'
        }), 400
    
    try:
        success, result = sdk.get_image()
        if not success:
            return jsonify({
                'success': False,
                'error': f'Capture failed: {result}'
            }), 400
        
        image_data = result
        quality = sdk.get_image_quality(image_data)
        
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': image_b64,
            'quality': quality,
            'width': sdk.image_width,
            'height': sdk.image_height
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def cleanup():
    """Cleanup SDK resources"""
    global sdk
    if sdk:
        try:
            sdk.close_device()
            sdk.destroy()
        except:
            pass


if __name__ == '__main__':
    print("=" * 60)
    print("SecuGen Client Bridge for Django Web Integration")
    print("=" * 60)
    print()
    
    # Initialize SDK
    print("Initializing SecuGen SDK...")
    if not initialize_sdk():
        print("\n❌ Failed to initialize SDK. Please check:")
        print("   1. SecuGen device is connected")
        print("   2. sgfplib.dll is in the correct location")
        print("   3. All required DLL files are present")
        sys.exit(1)
    
    print()
    print("✓ SDK initialized successfully")
    print()
    print("=" * 60)
    print("Client Bridge Server Starting")
    print("=" * 60)
    print()
    print("API Endpoints:")
    print("  GET  http://localhost:5000/status        - Check device status")
    print("  POST http://localhost:5000/capture       - Capture fingerprint")
    print("  POST http://localhost:5000/match         - Match two templates")
    print("  GET  http://localhost:5000/live-preview  - Live preview frame")
    print()
    print("Server running on http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    try:
        app.run(host='127.0.0.1', port=5000, debug=False)
    finally:
        cleanup()