"""
Django Management Command to Import Employee Data from Excel
Place this file in: your_app/management/commands/import_employees.py
Usage: python manage.py import_employees /path/to/Employee_data.xlsx
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
import pandas as pd
import sys
from pathlib import Path


class Command(BaseCommand):
    help = 'Import employee data from Excel file and create User and EmployeeProfile records'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_file',
            type=str,
            help='Path to the Excel file containing employee data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving to database'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing records if they already exist'
        )
        parser.add_argument(
            '--default-password',
            type=str,
            default='ChangeMe@123',
            help='Default password for new users (default: ChangeMe@123)'
        )

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        dry_run = options['dry_run']
        update_mode = options['update']
        default_password = options['default_password']

        # Validate file exists
        if not Path(excel_file).exists():
            raise CommandError(f'File not found: {excel_file}')

        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS(f'Employee Data Import Tool'))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}'))
        self.stdout.write(f'Excel file: {excel_file}')
        self.stdout.write(f'Mode: {"DRY RUN (no changes)" if dry_run else "LIVE IMPORT"}')
        self.stdout.write(f'Update existing: {"Yes" if update_mode else "No"}')
        self.stdout.write(f'Default password: {default_password}')
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))
        
        try:
            df = pd.read_excel(excel_file)
        except Exception as e:
            raise CommandError(f'Error reading Excel file: {str(e)}')

        # Clean column names (remove extra spaces)
        df.columns = df.columns.str.strip()
        
        # Display file info
        self.stdout.write(f'📊 Total records found: {len(df)}')
        self.stdout.write(f'📋 Columns: {", ".join(df.columns.tolist())}\n')

        # Statistics
        stats = {
            'total': len(df),
            'created_users': 0,
            'created_profiles': 0,
            'updated_users': 0,
            'updated_profiles': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': []
        }

        # Track usernames to detect duplicates within this import batch
        username_tracker = {}  # {username: employee_code}

        # Process each row
        for index, row in df.iterrows():
            try:
                result = self.process_employee(row, dry_run, update_mode, default_password, username_tracker)
                
                if result['user_created']:
                    stats['created_users'] += 1
                if result['profile_created']:
                    stats['created_profiles'] += 1
                if result['user_updated']:
                    stats['updated_users'] += 1
                if result['profile_updated']:
                    stats['updated_profiles'] += 1
                if result['skipped']:
                    stats['skipped'] += 1
                    
            except Exception as e:
                stats['errors'] += 1
                error_msg = f'Row {index + 2} (Emp Code: {row.get("Emp Code", "N/A")}): {str(e)}'
                stats['error_details'].append(error_msg)
                self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))

        # Display summary
        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS('IMPORT SUMMARY'))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}'))
        self.stdout.write(f'Total records processed: {stats["total"]}')
        self.stdout.write('')
        
        if stats["created_users"] > 0:
            self.stdout.write(self.style.SUCCESS(f'✅ Users created: {stats["created_users"]}'))
        if stats["created_profiles"] > 0:
            self.stdout.write(self.style.SUCCESS(f'✅ Profiles created: {stats["created_profiles"]}'))
        
        if update_mode:
            if stats["updated_users"] > 0:
                self.stdout.write(self.style.WARNING(f'🔄 Users updated: {stats["updated_users"]}'))
            if stats["updated_profiles"] > 0:
                self.stdout.write(self.style.WARNING(f'🔄 Profiles updated: {stats["updated_profiles"]}'))
        
        if stats['skipped'] > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Skipped (already exists): {stats["skipped"]}'))
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errors: {stats["errors"]}'))
            self.stdout.write('\nError details:')
            for error in stats['error_details']:
                self.stdout.write(f'  - {error}')
        
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('This was a DRY RUN. No changes were made to the database.'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to perform actual import.\n'))

    @transaction.atomic
    def process_employee(self, row, dry_run=False, update_mode=False, default_password='ChangeMe@123', username_tracker=None):
        """Process a single employee record"""
        # Import here to avoid issues if models aren't ready
        from process_dojo.models import EmployeeProfile  # Update 'process_dojo' to your app name
        
        if username_tracker is None:
            username_tracker = {}
        
        result = {
            'user_created': False,
            'profile_created': False,
            'user_updated': False,
            'profile_updated': False,
            'skipped': False
        }

        # Extract and clean data from row
        emp_code = str(row['Emp Code']).strip()
        first_name = str(row['Employee First Name']).strip() if pd.notna(row['Employee First Name']) else ''
        last_name = str(row['Employee Last Name']).strip() if pd.notna(row['Employee Last Name']) else ''
        username = str(row['User Name']).strip().lower() if pd.notna(row['User Name']) else emp_code.lower()
        
        # AUTO-FIX: Make username unique
        original_username = username
        
        # Check duplicates in BOTH current import batch AND database
        while True:
            # Check if username is already used in this import batch
            if username in username_tracker and username_tracker[username] != emp_code:
                # Duplicate in current batch - append employee code
                username = f"{original_username}.{emp_code.lower()}"
                if username in username_tracker and username_tracker[username] != emp_code:
                    # Even with emp_code it exists in batch, add counter
                    counter = 1
                    while f"{original_username}.{emp_code.lower()}.{counter}" in username_tracker:
                        counter += 1
                    username = f"{original_username}.{emp_code.lower()}.{counter}"
                break
            
            # Check if username exists in database
            if User.objects.filter(username=username).exists():
                # Check if this username belongs to this employee's profile
                try:
                    existing_user = User.objects.get(username=username)
                    if hasattr(existing_user, 'employee_profile') and existing_user.employee_profile.employee_id == emp_code:
                        # This username already belongs to this employee
                        break
                except User.DoesNotExist:
                    pass
                
                # Username exists in DB and belongs to someone else
                username = f"{original_username}.{emp_code.lower()}"
                if User.objects.filter(username=username).exists():
                    # Even with emp_code it exists, add a number
                    counter = 1
                    while User.objects.filter(username=f"{original_username}.{emp_code.lower()}.{counter}").exists():
                        counter += 1
                    username = f"{original_username}.{emp_code.lower()}.{counter}"
                break
            
            # Username is unique - use it
            break
        
        # Register this username in tracker for this import batch
        username_tracker[username] = emp_code
        
        # Handle email - create default if missing or invalid
        email = str(row['Email']).strip() if pd.notna(row['Email']) else ''
        if not email or email == 'nan' or '@' not in email:
            email = f'{username}@company.local'
        
        # Use provided password or default
        password = str(row['Password']).strip() if pd.notna(row['Password']) else default_password
        if not password or password == 'nan':
            password = default_password
            
        plant = str(row['Palnt']).strip() if pd.notna(row['Palnt']) else 'Unknown'  # Note: typo in Excel column name
        unit = str(row['Unit']).strip() if pd.notna(row['Unit']) else 'Unknown'

        # Show username modification in dry run
        username_note = f" [Auto-fixed: {original_username} → {username}]" if username != original_username else ""
        
        if dry_run:
            self.stdout.write(
                f'[DRY RUN] Would process: {emp_code} - {first_name} {last_name} ({username}){username_note} | {plant} / {unit}'
            )
            return result

        # Check if user exists
        user_exists = User.objects.filter(username=username).exists()
        
        if user_exists and not update_mode:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Skipping {emp_code} - User "{username}" already exists')
            )
            result['skipped'] = True
            return result

        # Show if username was auto-modified
        if username != original_username:
            self.stdout.write(
                self.style.WARNING(f'🔧 Auto-fixed duplicate username: {original_username} → {username}')
            )

        # Create or update User
        if user_exists:
            user = User.objects.get(username=username)
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()
            result['user_updated'] = True
            self.stdout.write(
                self.style.WARNING(f'🔄 Updated user: {username} ({first_name} {last_name})')
            )
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            result['user_created'] = True
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created user: {username} ({first_name} {last_name})')
            )

        # Create or update EmployeeProfile
        profile, created = EmployeeProfile.objects.update_or_create(
            user=user,
            defaults={
                'employee_id': emp_code,
                'plant': plant,
                'unit': unit,
                'department': 'Not Specified',  # You can modify this if department data is available
            }
        )
        
        if created:
            result['profile_created'] = True
            self.stdout.write(
                f'   ✅ Created profile: {emp_code} | Plant: {plant} | Unit: {unit}'
            )
        else:
            result['profile_updated'] = True
            self.stdout.write(
                f'   🔄 Updated profile: {emp_code} | Plant: {plant} | Unit: {unit}'
            )

        return result