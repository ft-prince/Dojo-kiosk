"""
Management command to load sample data for Process DOJO
Usage: python manage.py load_sample_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from process_dojo.models import (
    Unit, Line, Operation, TrainingVideo, MCQTest, Question,
    EmployeeProfile
)


class Command(BaseCommand):
    help = 'Load sample training data for Process DOJO system'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading sample data...\n'))
        
        # Create Units
        self.stdout.write('Creating Units...')
        els = Unit.objects.create(
            name="ELS",
            description="Engine Line System",
            is_active=True
        )
        
        amt = Unit.objects.create(
            name="AMT",
            description="Advanced Manufacturing Technology",
            is_active=True
        )
        
        unit3 = Unit.objects.create(
            name="UNIT-3",
            description="Production Unit 3",
            is_active=True
        )
        
        # Create Lines
        self.stdout.write('Creating Lines...')
        red_line = Line.objects.create(
            unit=els,
            name="RED LINE",
            description="Primary assembly line",
            is_active=True
        )
        
        tata_line = Line.objects.create(
            unit=els,
            name="TATA LINE",
            description="TATA vehicle assembly",
            is_active=True
        )
        
        mahindra_line = Line.objects.create(
            unit=amt,
            name="MAHINDRA LINE",
            description="Mahindra vehicle assembly",
            is_active=True
        )
        
        vg_line = Line.objects.create(
            unit=amt,
            name="VG LINE",
            description="VG series assembly",
            is_active=True
        )
        
        pre_assy = Line.objects.create(
            unit=unit3,
            name="PRE-ASSY",
            description="Pre-assembly operations",
            is_active=True
        )
        
        # Create Operations
        self.stdout.write('Creating Operations...')
        operations = [
            {
                'line': red_line,
                'name': 'OP-100 PLUGGING',
                'code': 'OP-100',
                'ctq': True,
                'order': 1
            },
            {
                'line': red_line,
                'name': 'OP-123 OPV',
                'code': 'OP-123',
                'ctq': True,
                'order': 2
            },
            {
                'line': red_line,
                'name': 'OP-125 CLUTCH PISTION',
                'code': 'OP-125',
                'ctq': False,
                'order': 3
            },
            {
                'line': tata_line,
                'name': 'OP-130 NRV',
                'code': 'OP-130',
                'ctq': True,
                'order': 1
            },
            {
                'line': tata_line,
                'name': 'OP-150 CPS',
                'code': 'OP-150',
                'ctq': False,
                'order': 2
            },
            {
                'line': mahindra_line,
                'name': 'OP-200 ASSEMBLY',
                'code': 'OP-200',
                'ctq': True,
                'order': 1
            },
            {
                'line': vg_line,
                'name': 'OP-300 TESTING',
                'code': 'OP-300',
                'ctq': True,
                'order': 1
            },
            {
                'line': pre_assy,
                'name': 'OP-400 PREP',
                'code': 'OP-400',
                'ctq': False,
                'order': 1
            },
        ]
        
        created_operations = []
        for op_data in operations:
            operation = Operation.objects.create(
                line=op_data['line'],
                name=op_data['name'],
                operation_code=op_data['code'],
                is_ctq_station=op_data['ctq'],
                is_active=True,
                order=op_data['order']
            )
            created_operations.append(operation)
        
        # Create sample employees
        self.stdout.write('Creating Sample Employees...')
        sample_users = [
            {
                'username': 'operator001',
                'password': 'demo123',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'employee_id': 'EMP001',
                'plant': 'Plant-A',
                'unit': 'ELS',
                'department': 'Assembly'
            },
            {
                'username': 'operator002',
                'password': 'demo123',
                'first_name': 'Priya',
                'last_name': 'Sharma',
                'employee_id': 'EMP002',
                'plant': 'Plant-A',
                'unit': 'AMT',
                'department': 'Quality'
            },
            {
                'username': 'operator003',
                'password': 'demo123',
                'first_name': 'Amit',
                'last_name': 'Patel',
                'employee_id': 'EMP003',
                'plant': 'Plant-B',
                'unit': 'UNIT-3',
                'department': 'Production'
            },
        ]
        
        for user_data in sample_users:
            user = User.objects.create_user(
                username=user_data['username'],
                password=user_data['password'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name']
            )
            
            EmployeeProfile.objects.create(
                user=user,
                employee_id=user_data['employee_id'],
                plant=user_data['plant'],
                unit=user_data['unit'],
                department=user_data['department']
            )
        
        # Note: Videos and MCQ tests need actual files, so we'll create placeholders
        self.stdout.write(
            self.style.WARNING(
                '\nNote: Training videos need to be uploaded manually via admin.'
            )
        )
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Sample data loaded successfully!\n')
        )
        self.stdout.write('Created:')
        self.stdout.write(f'  - {Unit.objects.count()} Units')
        self.stdout.write(f'  - {Line.objects.count()} Lines')
        self.stdout.write(f'  - {Operation.objects.count()} Operations')
        self.stdout.write(f'  - {User.objects.count() - 1} Sample Employees')  # -1 for admin
        
        self.stdout.write('\nSample login credentials:')
        self.stdout.write('  Username: operator001, Password: demo123')
        self.stdout.write('  Username: operator002, Password: demo123')
        self.stdout.write('  Username: operator003, Password: demo123')
        
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Login to admin panel')
        self.stdout.write('2. Upload training videos for operations')
        self.stdout.write('3. Create MCQ tests for videos')
        self.stdout.write('4. Test the operator workflow')