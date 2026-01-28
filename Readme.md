# Process DOJO - Biometric Authentication System

## Overview

Process DOJO is a Django-based training kiosk application with SecuGen fingerprint authentication. It provides offline training through video-based learning and MCQ testing, with biometric login/logout for employees.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Django Web Application                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Models     │  │    Views     │  │  Biometric   │      │
│  │              │  │              │  │   Service    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ HTTP API (localhost:5000)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SecuGen Client Bridge (Flask)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Python SDK Wrapper (secugen_wrapper.py)      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ ctypes → sgfplib.dll
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SecuGen FDx SDK Pro (Native DLL)                │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ USB Connection
                              ▼
                    ┌──────────────────┐
                    │  SecuGen Device  │
                    │  (Fingerprint    │
                    │   Scanner)       │
                    └──────────────────┘
```

## Key Components

### 1. Django Models (`models.py`)

**Core Models:**
- **EmployeeProfile**: Extended user profile with `biometric_id` for fingerprint enrollment
- **LoginSession**: Tracks login/logout times and session duration
- **Unit/Line/Operation**: Training hierarchy structure
- **TrainingVideo**: Video training content
- **MCQTest/Question**: Testing infrastructure
- **VideoCompletion/TestAttempt**: Progress tracking

### 2. Biometric Views (`biometric_views.py`)

**Authentication Endpoints:**
- `biometric_login_view`: Login page with fingerprint scanner interface
- `biometric_authenticate`: API endpoint for fingerprint matching (1:N identification)
- `biometric_logout_view`: Logout with session duration tracking

**Enrollment Endpoints (Admin Only):**
- `biometric_enrollment_list`: List all employees with enrollment status
- `biometric_enrollment_form`: Fingerprint capture interface
- `biometric_enroll_save`: Save captured fingerprint template
- `biometric_delete`: Delete enrolled fingerprint

**Health Check:**
- `biometric_device_status`: Check scanner connection status

### 3. Biometric Service (`biometric_service.py`)

**BiometricDatabase Class:**
- Stores fingerprint templates and images in filesystem
- Path: `MEDIA_ROOT/biometric_data/`
- Format: `{biometric_id}.template` (template bytes), `{biometric_id}.png` (image)
- Links to EmployeeProfile via `biometric_id` field

**BiometricService Class:**
- High-level API for enrollment, identification, and verification
- Uses client bridge for template matching (requires device access)
- Methods:
  - `enroll_user()`: Save fingerprint template and image
  - `identify_user()`: 1:N matching against all enrolled users
  - `verify_user()`: 1:1 verification for specific user
  - `delete_user_fingerprint()`: Remove enrollment
  - `get_user_fingerprint_image()`: Retrieve stored image

### 4. SecuGen Client Bridge (`secugen_client_bridge.py`)

Flask application running on `localhost:5000` providing HTTP API for browser access.

**API Endpoints:**
- `GET /status`: Check device connection status
- `POST /capture`: Capture fingerprint (returns image + template + quality)
- `POST /match`: Match two fingerprint templates
- `GET /live-preview`: Single frame capture for live preview

**Why Client Bridge?**
The SecuGen SDK requires direct USB device access through native DLLs, which browsers cannot provide. The client bridge runs locally and acts as a proxy between the web application and the fingerprint scanner.

### 5. SecuGen SDK Wrapper (`secugen_wrapper.py`)

Python ctypes wrapper for `sgfplib.dll` providing:
- Device initialization and control
- Image capture from scanner
- Template creation from images
- Template matching with configurable security levels
- Quality assessment

## Installation & Setup

### Prerequisites

1. **Hardware:**
   - SecuGen fingerprint scanner (USB)
   - Windows PC (kiosk machine)

2. **Software:**
   - Python 3.8+
   - Django 3.2+
   - Flask + Flask-CORS
   - SecuGen FDx SDK Pro DLL files

### Step 1: Django Project Setup

```bash
# Install dependencies
pip install django pillow requests

# Configure settings.py
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Optional: Specify DLL path
SECUGEN_DLL_PATH = r'C:\path\to\sgfplib.dll'
```

### Step 2: Database Migration

```bash
python manage.py makemigrations process_dojo
python manage.py migrate
```

### Step 3: SecuGen SDK Setup

Place the following files in your `biometric_sdk/` directory:
```
biometric_sdk/
├── sgfplib.dll           # Main SDK DLL (required)
├── secugen_wrapper.py    # Python wrapper
├── secugen_client_bridge.py  # Flask bridge
└── bin/
    └── x64/
        └── (additional DLL dependencies)
```

### Step 4: Start Client Bridge

**On the kiosk machine, run:**
```bash
cd biometric_sdk
python secugen_client_bridge.py
```

You should see:
```
✓ Device connected: 260x300
Client Bridge Server Starting
Server running on http://localhost:5000
```

### Step 5: Start Django Server

```bash
python manage.py runserver
```

## Usage Workflows

### Employee Enrollment (Admin)

1. **Navigate to Enrollment:**
   ```
   /process_dojo/biometric/enrollment/
   ```

2. **Select Employee:**
   - Click "Enroll" button next to employee name
   - System opens enrollment form

3. **Capture Fingerprint:**
   - JavaScript calls `POST http://localhost:5000/capture`
   - Client bridge captures from scanner
   - Returns: template (base64), image (base64), quality score

4. **Save Enrollment:**
   - Browser sends to Django: `POST /biometric/enroll/save/`
   - Django saves template and image to filesystem
   - Updates `EmployeeProfile.biometric_id`

**Files Created:**
```
media/biometric_data/
├── BIO_1_john_smith.template    # Binary template
└── BIO_1_john_smith.png         # Fingerprint image (260x300)
```

### Employee Login (Biometric)

1. **Navigate to Login:**
   ```
   /process_dojo/biometric/login/
   ```

2. **Scan Fingerprint:**
   - JavaScript calls `POST http://localhost:5000/capture`
   - Client bridge returns template

3. **Authenticate:**
   - Browser sends template to Django: `POST /biometric/authenticate/`
   - Django forwards to client bridge for matching: `POST http://localhost:5000/match`
   - Client bridge matches against all enrolled templates (1:N)
   - If match found:
     - Django creates `LoginSession` record
     - Logs user in via `django.contrib.auth.login()`
     - Redirects to dashboard

4. **Session Tracking:**
   ```python
   LoginSession.objects.create(
       user=matched_user,
       login_time=timezone.now()
   )
   ```

### Employee Logout

1. **Logout:**
   ```
   /process_dojo/biometric/logout/
   ```

2. **Session Closure:**
   - Updates `LoginSession.logout_time`
   - Calculates `session_duration_minutes`
   - Calls `django.contrib.auth.logout()`

## Matching Flow (1:N Identification)

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: User scans fingerprint at kiosk                    │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Client Bridge captures and creates template        │
│  POST /capture → returns base64 template                    │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Browser sends template to Django                   │
│  POST /biometric/authenticate/                              │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Django BiometricService.identify_user()            │
│  - Loads all enrolled users from DB                         │
│  - For each user:                                           │
│    1. Load stored template from filesystem                  │
│    2. Call Client Bridge: POST /match                       │
│    3. Client Bridge uses SDK to match templates             │
│    4. If matched → return User object                       │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Django logs in user and creates LoginSession       │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Settings

```python
# settings.py

# Biometric data storage
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Optional: Custom DLL path
SECUGEN_DLL_PATH = r'C:\SecuGen\sgfplib.dll'
```

### URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('process_dojo/', include('process_dojo.urls')),
    path('admin/', admin.site.urls),
]
```

## Database Schema

### EmployeeProfile
```sql
CREATE TABLE employee_profile (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES auth_user(id),
    employee_id VARCHAR(50) UNIQUE,
    plant VARCHAR(100),
    unit VARCHAR(100),
    department VARCHAR(100),
    biometric_id VARCHAR(100) UNIQUE,  -- Links to fingerprint files
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### LoginSession
```sql
CREATE TABLE login_session (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES auth_user(id),
    login_time TIMESTAMP,
    logout_time TIMESTAMP NULL,
    session_duration_minutes INTEGER DEFAULT 0
);
```

## Security Considerations

### Template Storage
- Templates stored as binary files on filesystem
- Filenames use biometric_id format: `BIO_{user_id}_{username}`
- Not directly accessible via web (outside STATIC/MEDIA_URL)

### Matching Security Level
- Default: Level 5 (balanced)
- Range: 1-9 (1=lenient, 9=strict)
- Configured in `SecuGenSDK.match_templates()`

### CSRF Protection
- Biometric endpoints use `@csrf_exempt` for API compatibility
- Protected by `@login_required` and `@user_passes_test` decorators
- Admin-only access for enrollment endpoints

### Access Control
```python
@login_required
@user_passes_test(lambda u: u.is_staff)
def biometric_enrollment_list(request):
    # Only staff can access enrollment
```

## Troubleshooting

### Client Bridge Won't Start

**Error:** `Failed to load library`
- **Solution:** Ensure `sgfplib.dll` is in correct location
- Check paths: `./sgfplib.dll`, `./bin/x64/sgfplib.dll`, `C:\SecuGen\sgfplib.dll`

**Error:** `Failed to open device`
- **Solution:** 
  - Check USB connection
  - Install SecuGen device drivers
  - Check Windows Device Manager

### Matching Fails

**Error:** `No match found`
- **Possible causes:**
  - Poor quality fingerprint (quality < 50)
  - Security level too high
  - Template corruption
  - Wrong finger used

**Debug steps:**
1. Check quality score during capture
2. Re-enroll with better quality scan
3. Lower security level temporarily for testing
4. Check client bridge logs for matching details

### Client Bridge Not Accessible

**Error:** `Failed to connect to client bridge`
- **Solution:**
  - Ensure client bridge is running: `python secugen_client_bridge.py`
  - Check Flask logs for errors
  - Verify port 5000 is not blocked by firewall
  - Test manually: `curl http://localhost:5000/status`

### Image Quality Issues

**Low quality scores (<50):**
- Clean fingerprint scanner surface
- Ensure proper finger placement
- Adjust finger pressure (not too light, not too heavy)
- Re-scan if quality too low

### PNG Conversion Errors

**Error:** `Image save failed`
- **Cause:** Incorrect image dimensions
- **Solution:** SDK wrapper auto-detects common SecuGen dimensions:
  - 260x300 (most common)
  - 300x400
  - 320x400
- Check `biometric_service.py` logs for dimension detection

## API Reference

### Client Bridge API

#### POST /capture
Capture fingerprint from scanner.

**Response:**
```json
{
  "success": true,
  "image": "base64_encoded_image",
  "template": "base64_encoded_template",
  "quality": 85,
  "width": 260,
  "height": 300
}
```

#### POST /match
Match two fingerprint templates.

**Request:**
```json
{
  "template1": "base64_template_1",
  "template2": "base64_template_2"
}
```

**Response:**
```json
{
  "success": true,
  "matched": true
}
```

#### GET /status
Check device status.

**Response:**
```json
{
  "success": true,
  "connected": true,
  "width": 260,
  "height": 300
}
```

### Django Biometric API

#### POST /biometric/authenticate/
Authenticate user via fingerprint.

**Request:**
```json
{
  "template": "base64_encoded_template"
}
```

**Response (Success):**
```json
{
  "success": true,
  "user": {
    "username": "john_smith",
    "full_name": "John Smith",
    "employee_id": "EMP001",
    "plant": "Plant A",
    "unit": "Unit 1",
    "department": "Production"
  },
  "redirect_url": "/process_dojo/"
}
```

**Response (Failure):**
```json
{
  "success": false,
  "error": "Fingerprint not recognized. Please try again."
}
```

#### POST /biometric/enroll/save/
Save enrolled fingerprint.

**Request:**
```json
{
  "employee_id": "EMP001",
  "template": "base64_template",
  "image": "base64_image",
  "quality": 85
}
```

**Response:**
```json
{
  "success": true,
  "message": "Fingerprint enrolled successfully for John Smith",
  "biometric_id": "BIO_1_john_smith"
}
```

## Reports & Analytics

### Login Session Report
```python
# View: LoginSessionReportView
# URL: /process_dojo/reports/logins/

# Shows:
- Total sessions
- Average session duration
- Login/logout times
- Session duration breakdown
```

### Employee Report
```python
# View: EmployeeReportView
# URL: /process_dojo/reports/employee/

# Shows per employee:
- Video completion count
- Test attempts and pass rate
- Total learning time
- Last activity timestamp
```

## Performance Considerations

### Matching Speed
- 1:N matching scales with enrolled user count
- Typical: ~50-100ms per comparison
- 100 users ≈ 5-10 seconds total
- Consider caching or optimization for large deployments

### Template Size
- Typical: 400-600 bytes per template
- Images: ~78KB (260x300 grayscale PNG)
- Storage: Minimal (1000 users ≈ 80MB)

### Database Queries
- Use `select_related()` for user profiles
- Index on `biometric_id` field
- Session tracking uses efficient datetime queries

## Deployment Checklist

### Kiosk Setup
- [ ] Install Python 3.8+
- [ ] Install SecuGen drivers
- [ ] Copy application code
- [ ] Install Django dependencies
- [ ] Copy `sgfplib.dll` and dependencies
- [ ] Configure `MEDIA_ROOT` path
- [ ] Run migrations
- [ ] Create superuser
- [ ] Start client bridge (background service)
- [ ] Start Django server
- [ ] Test device connection
- [ ] Enroll test users
- [ ] Test login/logout flow

### Production Considerations
- [ ] Use production WSGI server (gunicorn/waitress)
- [ ] Configure client bridge as Windows service
- [ ] Set up automatic restart on failure
- [ ] Configure firewall rules for localhost:5000
- [ ] Back up biometric data directory
- [ ] Set up log rotation
- [ ] Monitor disk space for session logs
- [ ] Configure session timeout settings

## Maintenance

### Regular Tasks
1. **Database backup** (weekly)
   - Export LoginSession data
   - Archive old session records

2. **Clean old sessions** (monthly)
   ```python
   # Delete sessions older than 6 months
   from datetime import timedelta
   cutoff = timezone.now() - timedelta(days=180)
   LoginSession.objects.filter(login_time__lt=cutoff).delete()
   ```

3. **Scanner maintenance** (as needed)
   - Clean scanner surface with soft cloth
   - Check USB connection
   - Verify device drivers

### Updates
- Keep Django updated for security patches
- Monitor SecuGen SDK updates
- Test updates in staging environment first

## Support & Resources

### SecuGen Documentation
- SDK Manual: Check SecuGen developer portal
- Device drivers: https://www.secugen.com/support/

### Django Resources
- Documentation: https://docs.djangoproject.com/
- Authentication: https://docs.djangoproject.com/en/stable/topics/auth/



**Version:** 1.0  
**Last Updated:** JAN 2026  
