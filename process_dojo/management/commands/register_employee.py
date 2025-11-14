"""
Management command to register employees with biometric data
Usage: python manage.py register_employee
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from process_dojo.models import EmployeeProfile
import getpass


class Command(BaseCommand):
    help = 'Register a new employee with biometric ID and profile details'
    
    def add_arguments(self, parser):
        parser.add_argument('--batch', action='store_true', help='Batch mode (no interactive prompts)')
        parser.add_argument('--username', type=str, help='Username')
        parser.add_argument('--password', type=str, help='Password')
        parser.add_argument('--employee-id', type=str, help='Employee ID')
        parser.add_argument('--first-name', type=str, help='First name')
        parser.add_argument('--last-name', type=str, help='Last name')
        parser.add_argument('--email', type=str, help='Email address')
        parser.add_argument('--plant', type=str, help='Plant name')
        parser.add_argument('--unit', type=str, help='Unit name')
        parser.add_argument('--department', type=str, help='Department name')
        parser.add_argument('--biometric-id', type=str, help='Biometric ID')
    
    def handle(self, *args, **options):
        if options['batch']:
            self.batch_mode(options)
        else:
            self.interactive_mode()
    
    def interactive_mode(self):
        """Interactive employee registration"""
        self.stdout.write(self.style.SUCCESS('=== Employee Registration ===\n'))
        
        # User details
        username = input('Username: ')
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User {username} already exists!'))
            return
        
        password = getpass.getpass('Password: ')
        password_confirm = getpass.getpass('Confirm Password: ')
        
        if password != password_confirm:
            self.stdout.write(self.style.ERROR('Passwords do not match!'))
            return
        
        first_name = input('First Name: ')
        last_name = input('Last Name: ')
        email = input('Email (optional): ')
        
        # Employee profile details
        employee_id = input('Employee ID: ')
        
        if EmployeeProfile.objects.filter(employee_id=employee_id).exists():
            self.stdout.write(self.style.ERROR(f'Employee ID {employee_id} already exists!'))
            return
        
        plant = input('Plant: ')
        unit = input('Unit: ')
        department = input('Department: ')
        biometric_id = input('Biometric ID (optional): ')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email
        )
        
        # Create employee profile
        profile = EmployeeProfile.objects.create(
            user=user,
            employee_id=employee_id,
            plant=plant,
            unit=unit,
            department=department,
            biometric_id=biometric_id if biometric_id else None
        )
        
        self.stdout.write(self.style.SUCCESS(f'\nEmployee registered successfully!'))
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Employee ID: {employee_id}')
        self.stdout.write(f'Plant/Unit: {plant}/{unit}')
    
    def batch_mode(self, options):
        """Batch mode for automated registration"""
        required_fields = ['username', 'password', 'employee_id', 'plant', 'unit', 'department']
        
        for field in required_fields:
            if not options[field]:
                self.stdout.write(self.style.ERROR(f'--{field} is required in batch mode'))
                return
        
        username = options['username']
        employee_id = options['employee_id']
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User {username} already exists!'))
            return
        
        if EmployeeProfile.objects.filter(employee_id=employee_id).exists():
            self.stdout.write(self.style.ERROR(f'Employee ID {employee_id} already exists!'))
            return
        
        # Create user
        user = User.objects.create_user(
            username=username,
            password=options['password'],
            first_name=options.get('first_name', ''),
            last_name=options.get('last_name', ''),
            email=options.get('email', '')
        )
        
        # Create employee profile
        profile = EmployeeProfile.objects.create(
            user=user,
            employee_id=employee_id,
            plant=options['plant'],
            unit=options['unit'],
            department=options['department'],
            biometric_id=options.get('biometric_id')
        )
        
        self.stdout.write(self.style.SUCCESS(f'Employee {employee_id} registered successfully!'))