"""
Management command to load Safety Training data for Process DOJO
This script:
1. Clears all existing data
2. Loads comprehensive safety training modules with realistic MCQs

Usage: python manage.py load_safety_training
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import transaction
from process_dojo.models import (
    Unit, Line, Operation, TrainingVideo, MCQTest, Question,
    EmployeeProfile, VideoCompletion, TestAttempt, SavedAnswer, LoginSession
)


class Command(BaseCommand):
    help = 'Clear all data and load Safety Training modules'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-admin',
            action='store_true',
            help='Keep admin/superuser accounts',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(self.style.WARNING('⚠️  SAFETY TRAINING DATA LOADER'))
        self.stdout.write(self.style.WARNING('='*70))
        
        # Clear existing data
        self.stdout.write('\n🗑️  Step 1: Clearing existing data...')
        self.clear_all_data(keep_admin=options['keep_admin'])
        
        # Load new safety training data
        self.stdout.write('\n📚 Step 2: Loading Safety Training modules...')
        self.load_safety_training()
        
        # Create sample employees
        self.stdout.write('\n👥 Step 3: Creating training users...')
        self.create_sample_users()
        
        # Print summary
        self.print_summary()
    
    def clear_all_data(self, keep_admin=False):
        """Clear all existing data from database"""
        with transaction.atomic():
            # Delete in correct order (child tables first)
            self.stdout.write('  Deleting saved answers...')
            SavedAnswer.objects.all().delete()
            
            self.stdout.write('  Deleting test attempts...')
            TestAttempt.objects.all().delete()
            
            self.stdout.write('  Deleting video completions...')
            VideoCompletion.objects.all().delete()
            
            self.stdout.write('  Deleting login sessions...')
            LoginSession.objects.all().delete()
            
            self.stdout.write('  Deleting MCQ questions...')
            Question.objects.all().delete()
            
            self.stdout.write('  Deleting MCQ tests...')
            MCQTest.objects.all().delete()
            
            self.stdout.write('  Deleting training videos...')
            TrainingVideo.objects.all().delete()
            
            self.stdout.write('  Deleting operations...')
            Operation.objects.all().delete()
            
            self.stdout.write('  Deleting lines...')
            Line.objects.all().delete()
            
            self.stdout.write('  Deleting units...')
            Unit.objects.all().delete()
            
            self.stdout.write('  Deleting employee profiles...')
            EmployeeProfile.objects.all().delete()
            
            # Delete users (except admin if keep_admin is True)
            if keep_admin:
                self.stdout.write('  Deleting non-admin users...')
                User.objects.filter(is_superuser=False).delete()
                self.stdout.write(self.style.SUCCESS('  ✓ Kept admin/superuser accounts'))
            else:
                self.stdout.write('  Deleting all users...')
                User.objects.all().delete()
                self.stdout.write(self.style.WARNING('  ⚠️  All users deleted (including admin)'))
        
        self.stdout.write(self.style.SUCCESS('✓ All data cleared successfully'))
    
    def load_safety_training(self):
        """Load safety training modules"""
        
        # Create Safety Training Unit
        safety_unit = Unit.objects.create(
            name="SAFETY TRAINING",
            description="Workplace Safety & Compliance Training Programs",
            is_active=True
        )
        self.stdout.write(f'  ✓ Created unit: {safety_unit.name}')
        
        # Create Safety Lines
        general_safety = Line.objects.create(
            unit=safety_unit,
            name="GENERAL SAFETY",
            description="Essential workplace safety practices and protocols",
            is_active=True
        )
        
        lab_safety = Line.objects.create(
            unit=safety_unit,
            name="LABORATORY SAFETY",
            description="Laboratory safety procedures and entry protocols",
            is_active=True
        )
        
        equipment_safety = Line.objects.create(
            unit=safety_unit,
            name="EQUIPMENT SAFETY",
            description="Safe operation of equipment and machinery",
            is_active=True
        )
        
        workplace_safety = Line.objects.create(
            unit=safety_unit,
            name="WORKPLACE SAFETY",
            description="Workplace organization and safety standards",
            is_active=True
        )
        
        vehicle_safety = Line.objects.create(
            unit=safety_unit,
            name="VEHICULAR SAFETY",
            description="On-premises vehicle operation and safety",
            is_active=True
        )
        
        self.stdout.write(f'  ✓ Created {Line.objects.count()} safety lines')
        
        # 1. Near Miss - Helmet Safety
        self.create_safety_module(
            line=general_safety,
            name='NEAR MISS - HELMET SAFETY',
            code='SAF-001',
            is_ctq=True,
            order=1,
            description='Understanding near-miss incidents and importance of wearing helmets in designated areas',
            video_title='Animated Safety Training: Near Miss - Helmet',
            video_desc='Learn to identify near-miss situations, understand the critical importance of wearing safety helmets, and recognize helmet-required zones in the workplace.',
            duration=180,
            has_voice=True,
            has_callouts=True,
            mcq_data={
                'title': 'Helmet Safety & Near Miss Assessment',
                'description': 'Test your understanding of near-miss reporting and helmet safety',
                'passing_score': 80,
                'time_limit': 10,
                'questions': [
                    {
                        'text': 'What is a "near miss" incident?',
                        'options': {
                            'A': 'An accident that resulted in injury',
                            'B': 'An event that could have caused harm but did not',
                            'C': 'A planned safety drill',
                            'D': 'A violation of safety rules'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'A near miss is an unplanned event that did not result in injury or damage but had the potential to do so.'
                    },
                    {
                        'text': 'Why is it important to report near-miss incidents?',
                        'options': {
                            'A': 'To punish workers',
                            'B': 'To prevent future accidents by identifying hazards',
                            'C': 'It is not important',
                            'D': 'To complete paperwork'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Reporting near misses helps identify and eliminate hazards before they cause actual injuries.'
                    },
                    {
                        'text': 'When must you wear a safety helmet?',
                        'options': {
                            'A': 'Only when supervisor is present',
                            'B': 'At all times in designated hard hat areas',
                            'C': 'Only during dangerous operations',
                            'D': 'Only if you feel unsafe'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Safety helmets must be worn continuously in all designated hard hat areas.'
                    },
                    {
                        'text': 'What should you do if you witness a near-miss incident?',
                        'options': {
                            'A': 'Ignore it since no one was hurt',
                            'B': 'Report it immediately to your supervisor',
                            'C': 'Wait until end of shift to report',
                            'D': 'Only report if damage occurred'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Immediate reporting allows quick corrective action to prevent future incidents.'
                    },
                    {
                        'text': 'Which type of helmet damage requires immediate replacement?',
                        'options': {
                            'A': 'Minor scratches on surface',
                            'B': 'Faded color',
                            'C': 'Cracks, dents, or impact damage',
                            'D': 'Worn chin strap only'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'Any structural damage like cracks or dents compromises helmet protection and requires immediate replacement.'
                    }
                ]
            }
        )
        
        # 2. Lab Entry Protocol
        self.create_safety_module(
            line=lab_safety,
            name='LAB ENTRY PROTOCOL',
            code='SAF-002',
            is_ctq=True,
            order=1,
            description='Mandatory procedures for entering laboratory areas safely',
            video_title='Lab Entry Protocol (Abridged)',
            video_desc='Essential safety protocols for laboratory entry including PPE requirements, authorization procedures, and contamination prevention measures.',
            duration=240,
            has_voice=True,
            has_callouts=True,
            mcq_data={
                'title': 'Laboratory Entry Protocol Assessment',
                'description': 'Verify your knowledge of lab entry procedures',
                'passing_score': 85,
                'time_limit': 12,
                'questions': [
                    {
                        'text': 'What is the first step before entering a laboratory?',
                        'options': {
                            'A': 'Put on lab coat',
                            'B': 'Verify authorization and check entry requirements',
                            'C': 'Wash hands',
                            'D': 'Sign logbook'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Always verify you are authorized and understand entry requirements before proceeding.'
                    },
                    {
                        'text': 'Which PPE is mandatory for ALL laboratory entries?',
                        'options': {
                            'A': 'Safety goggles and closed-toe shoes',
                            'B': 'Gloves only',
                            'C': 'Lab coat only',
                            'D': 'Face shield'
                        },
                        'correct': 'A',
                        'marks': 2,
                        'explanation': 'Safety goggles and closed-toe shoes are minimum required PPE for any lab entry.'
                    },
                    {
                        'text': 'What should you do if you find emergency exits blocked in the lab?',
                        'options': {
                            'A': 'Continue working, report later',
                            'B': 'Immediately report and do not enter until cleared',
                            'C': 'Move obstacles yourself',
                            'D': 'Use alternate exit'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Blocked exits are a critical safety violation requiring immediate reporting and resolution.'
                    },
                    {
                        'text': 'Can you eat or drink inside the laboratory?',
                        'options': {
                            'A': 'Yes, in designated areas only',
                            'B': 'Yes, if careful',
                            'C': 'No, absolutely prohibited',
                            'D': 'Yes, during breaks'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'Eating and drinking are strictly prohibited in laboratories to prevent contamination and chemical exposure.'
                    },
                    {
                        'text': 'What information must be checked on the lab door before entry?',
                        'options': {
                            'A': 'Room number only',
                            'B': 'Hazard signs, authorized personnel, and special requirements',
                            'C': 'Temperature setting',
                            'D': 'Cleaning schedule'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Door signage provides critical safety information including hazards and entry requirements.'
                    },
                    {
                        'text': 'When should you wash your hands in relation to lab work?',
                        'options': {
                            'A': 'Only after work',
                            'B': 'Only if hands are visibly dirty',
                            'C': 'Before entering and after exiting the lab',
                            'D': 'Not necessary if wearing gloves'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'Hand washing before and after lab work prevents contamination spread.'
                    }
                ]
            }
        )
        
        # 3. Rigging & Lifting Safety
        self.create_safety_module(
            line=equipment_safety,
            name='RIGGING & LIFTING SAFETY',
            code='SAF-003',
            is_ctq=True,
            order=1,
            description='Safe rigging practices and lifting operations for heavy loads',
            video_title='Rigging & Lifting Safety Training',
            video_desc='Comprehensive guide to safe rigging techniques, load calculations, equipment inspection, and proper lifting procedures to prevent accidents and equipment damage.',
            duration=420,
            has_voice=True,
            has_callouts=True,
            mcq_data={
                'title': 'Rigging & Lifting Safety Certification',
                'description': 'Test your rigging and lifting safety knowledge',
                'passing_score': 85,
                'time_limit': 15,
                'questions': [
                    {
                        'text': 'What is the first step in any lifting operation?',
                        'options': {
                            'A': 'Attach the load',
                            'B': 'Conduct a risk assessment and plan the lift',
                            'C': 'Start the crane',
                            'D': 'Signal the operator'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Every lift must begin with proper planning and risk assessment to ensure safety.'
                    },
                    {
                        'text': 'What does SWL stand for in rigging?',
                        'options': {
                            'A': 'Standard Working Load',
                            'B': 'Safe Working Limit',
                            'C': 'Safe Working Load',
                            'D': 'Structural Weight Limit'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'SWL (Safe Working Load) is the maximum load that equipment can safely handle.'
                    },
                    {
                        'text': 'Before using a sling, what must you inspect?',
                        'options': {
                            'A': 'Color only',
                            'B': 'Cuts, wear, broken wires, and identification tags',
                            'C': 'Length only',
                            'D': 'Weight'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Thorough inspection of slings for damage and proper identification is mandatory before each use.'
                    },
                    {
                        'text': 'What angle provides maximum lifting capacity for slings?',
                        'options': {
                            'A': '30 degrees',
                            'B': '45 degrees',
                            'C': '60 degrees or less',
                            'D': '90 degrees'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'Sling angles of 60 degrees or less from vertical provide optimal capacity and safety.'
                    },
                    {
                        'text': 'Who can authorize a lifting operation?',
                        'options': {
                            'A': 'Any employee',
                            'B': 'Only certified and authorized personnel',
                            'C': 'Equipment operator',
                            'D': 'Anyone with experience'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Only personnel with proper certification and authorization can approve lifting operations.'
                    },
                    {
                        'text': 'What should you do if a load starts to swing during lifting?',
                        'options': {
                            'A': 'Continue the lift quickly',
                            'B': 'Stop the lift and stabilize before continuing',
                            'C': 'Let it swing naturally',
                            'D': 'Push it to stop swinging'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Any load instability requires immediate stop and stabilization before proceeding.'
                    },
                    {
                        'text': 'Can you stand under a suspended load?',
                        'options': {
                            'A': 'Yes, if wearing helmet',
                            'B': 'Yes, if load is secured',
                            'C': 'No, never under any circumstances',
                            'D': 'Yes, briefly for positioning'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'Standing under suspended loads is strictly prohibited due to catastrophic risk if load falls.'
                    }
                ]
            }
        )
        
        # 4. Improper Mobile Scaffolding
        self.create_safety_module(
            line=equipment_safety,
            name='MOBILE SCAFFOLDING SAFETY',
            code='SAF-004',
            is_ctq=True,
            order=2,
            description='Identifying and preventing improper mobile scaffolding use',
            video_title='Improper Mobile Scaffolding',
            video_desc='Learn to identify common mobile scaffolding hazards, understand proper setup procedures, and prevent falls and collapses through correct scaffolding practices.',
            duration=300,
            has_voice=True,
            has_callouts=True,
            mcq_data={
                'title': 'Mobile Scaffolding Safety Test',
                'description': 'Assess your scaffolding safety knowledge',
                'passing_score': 80,
                'time_limit': 12,
                'questions': [
                    {
                        'text': 'What is the most common cause of scaffolding accidents?',
                        'options': {
                            'A': 'Equipment failure',
                            'B': 'Improper assembly and lack of guardrails',
                            'C': 'Weather conditions',
                            'D': 'Worker error only'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Most scaffolding accidents result from improper assembly and missing fall protection.'
                    },
                    {
                        'text': 'Before moving a mobile scaffold, what must you check?',
                        'options': {
                            'A': 'Paint condition',
                            'B': 'All personnel are off, wheels are unlocked, path is clear',
                            'C': 'Weight only',
                            'D': 'Time of day'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Never move scaffold with people or materials on it; ensure clear path and unlocked wheels.'
                    },
                    {
                        'text': 'What is the minimum height requiring guardrails on scaffolding?',
                        'options': {
                            'A': '1 meter',
                            'B': '1.5 meters',
                            'C': '2 meters',
                            'D': 'Any height above ground level'
                        },
                        'correct': 'D',
                        'marks': 2,
                        'explanation': 'Guardrails are required at any working height to prevent falls.'
                    },
                    {
                        'text': 'What should you do if you notice damaged scaffold components?',
                        'options': {
                            'A': 'Use it carefully',
                            'B': 'Tag out, remove from service, report immediately',
                            'C': 'Repair it yourself',
                            'D': 'Continue using until convenient to replace'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Damaged scaffolding must be immediately removed from service and reported.'
                    },
                    {
                        'text': 'Who can erect or modify scaffolding?',
                        'options': {
                            'A': 'Any employee',
                            'B': 'Only trained and competent persons',
                            'C': 'Maintenance staff only',
                            'D': 'Contractors only'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Only properly trained and competent personnel can erect, dismantle, or modify scaffolding.'
                    },
                    {
                        'text': 'Can you use makeshift items (boxes, barrels) to extend scaffold height?',
                        'options': {
                            'A': 'Yes, if stable',
                            'B': 'Yes, for short periods',
                            'C': 'No, absolutely prohibited',
                            'D': 'Yes, with supervisor approval'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'Using makeshift items to increase scaffold height is extremely dangerous and strictly prohibited.'
                    }
                ]
            }
        )
        
        # 5. Good Housekeeping
        self.create_safety_module(
            line=workplace_safety,
            name='GOOD HOUSEKEEPING',
            code='SAF-005',
            is_ctq=False,
            order=1,
            description='Workplace organization and cleanliness for safety',
            video_title='Good Housekeeping Means Safe Workplace',
            video_desc='Understand how proper housekeeping prevents accidents, improves efficiency, and creates a safer work environment. Learn the 5S methodology and daily housekeeping practices.',
            duration=270,
            has_voice=True,
            has_callouts=True,
            mcq_data={
                'title': 'Workplace Housekeeping Assessment',
                'description': 'Test your housekeeping and workplace safety knowledge',
                'passing_score': 75,
                'time_limit': 10,
                'questions': [
                    {
                        'text': 'What does the "5S" methodology stand for?',
                        'options': {
                            'A': 'Sort, Set in order, Shine, Standardize, Sustain',
                            'B': 'Safety, Security, Sanitation, Storage, Sorting',
                            'C': 'Sweep, Scrub, Sort, Store, Secure',
                            'D': 'Speed, Safety, Storage, Systems, Standards'
                        },
                        'correct': 'A',
                        'marks': 2,
                        'explanation': '5S is: Sort, Set in order, Shine, Standardize, Sustain - a systematic approach to workplace organization.'
                    },
                    {
                        'text': 'Why is poor housekeeping a safety hazard?',
                        'options': {
                            'A': 'It looks unprofessional only',
                            'B': 'Creates trip hazards, fire risks, and hides other hazards',
                            'C': 'Not really a hazard',
                            'D': 'Only affects cleanliness'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Poor housekeeping creates multiple hazards including slips, trips, fires, and can hide other dangers.'
                    },
                    {
                        'text': 'Where should tools and materials be stored during breaks?',
                        'options': {
                            'A': 'Anywhere convenient',
                            'B': 'On the floor',
                            'C': 'In designated storage areas, not in walkways',
                            'D': 'Leave at workstation'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'All items must be stored properly in designated areas to prevent trip hazards.'
                    },
                    {
                        'text': 'What should you do with spilled liquids immediately?',
                        'options': {
                            'A': 'Let it dry naturally',
                            'B': 'Clean up immediately and mark wet areas',
                            'C': 'Report at end of shift',
                            'D': 'Ignore if small amount'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Spills create slip hazards and must be cleaned immediately with proper warning signs.'
                    },
                    {
                        'text': 'When should housekeeping activities be performed?',
                        'options': {
                            'A': 'Only at end of shift',
                            'B': 'Weekly',
                            'C': 'Continuously throughout the day',
                            'D': 'When supervisor inspects'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'Good housekeeping is continuous - clean as you go to maintain safe conditions.'
                    }
                ]
            }
        )
        
        # 6. On-Premises Vehicular Safety
        self.create_safety_module(
            line=vehicle_safety,
            name='VEHICULAR SAFETY - ON-PREMISES',
            code='SAF-006',
            is_ctq=True,
            order=1,
            description='Safe operation of vehicles within facility premises',
            video_title='On-Premises Vehicular Safety',
            video_desc='Essential safety procedures for operating forklifts, trucks, and other vehicles on company premises including speed limits, pedestrian awareness, and loading dock safety.',
            duration=360,
            has_voice=True,
            has_callouts=True,
            mcq_data={
                'title': 'On-Premises Vehicle Safety Test',
                'description': 'Verify your knowledge of on-site vehicle safety',
                'passing_score': 85,
                'time_limit': 12,
                'questions': [
                    {
                        'text': 'What is the maximum speed limit for vehicles on premises (unless otherwise posted)?',
                        'options': {
                            'A': '5 km/h',
                            'B': '10 km/h',
                            'C': '15 km/h',
                            'D': '20 km/h'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Standard on-premises speed limit is typically 10 km/h unless specific signage indicates otherwise.'
                    },
                    {
                        'text': 'Before operating a forklift, what must you do?',
                        'options': {
                            'A': 'Just start driving',
                            'B': 'Conduct pre-operation inspection and have valid certification',
                            'C': 'Check fuel only',
                            'D': 'Warm up engine'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Pre-operation inspection and valid certification are mandatory before operating any industrial vehicle.'
                    },
                    {
                        'text': 'Who has the right of way at intersections on premises?',
                        'options': {
                            'A': 'Larger vehicles',
                            'B': 'Loaded vehicles',
                            'C': 'Pedestrians always have right of way',
                            'D': 'First to arrive'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'Pedestrians always have absolute right of way in all areas.'
                    },
                    {
                        'text': 'What should you do when approaching blind corners or doorways?',
                        'options': {
                            'A': 'Speed up to pass quickly',
                            'B': 'Slow down, sound horn, and ensure area is clear',
                            'C': 'Proceed at normal speed',
                            'D': 'Flash lights only'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'At blind corners, slow down, alert others with horn, and verify area is clear before proceeding.'
                    },
                    {
                        'text': 'Can you use mobile phones while operating on-premises vehicles?',
                        'options': {
                            'A': 'Yes, if hands-free',
                            'B': 'Yes, for work calls only',
                            'C': 'No, absolutely prohibited while vehicle is moving',
                            'D': 'Yes, if careful'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'Mobile phone use is strictly prohibited while operating any vehicle to prevent distracted driving.'
                    },
                    {
                        'text': 'What must be done before reversing any vehicle?',
                        'options': {
                            'A': 'Sound horn only',
                            'B': 'Check mirrors and use spotter if visibility is limited',
                            'C': 'Reverse quickly',
                            'D': 'Assume area is clear'
                        },
                        'correct': 'B',
                        'marks': 2,
                        'explanation': 'Always check all around and use a spotter when visibility is restricted during reversing.'
                    },
                    {
                        'text': 'Where should you park on-premises vehicles?',
                        'options': {
                            'A': 'Anywhere convenient',
                            'B': 'In fire lanes temporarily',
                            'C': 'Only in designated parking areas, not blocking exits or aisles',
                            'D': 'Near building entrances'
                        },
                        'correct': 'C',
                        'marks': 2,
                        'explanation': 'Vehicles must only be parked in designated areas and never block exits, aisles, or emergency equipment.'
                    }
                ]
            }
        )
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {Operation.objects.count()} safety training modules'))
    
    def create_safety_module(self, line, name, code, is_ctq, order, description, 
                            video_title, video_desc, duration, has_voice, has_callouts, mcq_data):
        """Helper method to create safety training module"""
        
        # Create operation
        operation = Operation.objects.create(
            line=line,
            name=name,
            operation_code=code,
            description=description,
            is_ctq_station=is_ctq,
            is_active=True,
            order=order
        )
        
        # Create placeholder video (will be replaced with real video via admin)
        video_placeholder = b'>>> UPLOAD YOUR SAFETY VIDEO VIA ADMIN PANEL <<<\n\nVideo Title: ' + video_title.encode()
        
        # Create training video
        video = TrainingVideo.objects.create(
            operation=operation,
            title=video_title,
            description=video_desc,
            duration_seconds=duration,
            has_voice=has_voice,
            has_callouts=has_callouts,
            is_active=True,
            order=1
        )
        
        # Save placeholder
        video.video_file.save(
            f'{code.lower()}_safety.mp4',
            ContentFile(video_placeholder),
            save=True
        )
        
        # Create MCQ test
        test = MCQTest.objects.create(
            video=video,
            title=mcq_data['title'],
            description=mcq_data['description'],
            passing_score=mcq_data['passing_score'],
            time_limit_minutes=mcq_data['time_limit'],
            is_active=True
        )
        
        # Create questions
        for i, q_data in enumerate(mcq_data['questions'], 1):
            Question.objects.create(
                test=test,
                question_text=q_data['text'],
                option_a=q_data['options']['A'],
                option_b=q_data['options']['B'],
                option_c=q_data['options']['C'],
                option_d=q_data['options']['D'],
                correct_answer=q_data['correct'],
                marks=q_data['marks'],
                ordering=i,
                explanation=q_data.get('explanation', '')
            )
        
        self.stdout.write(f'    ✓ {name} ({len(mcq_data["questions"])} questions)')
        return operation
    
    def create_sample_users(self):
        """Create sample employee users"""
        users_data = [
            {
                'username': 'safety.officer',
                'password': 'safety123',
                'first_name': 'Arun',
                'last_name': 'Verma',
                'email': 'arun.verma@marelli.com',
                'employee_id': 'SAF001',
                'plant': 'Main Plant',
                'unit': 'SAFETY TRAINING',
                'department': 'Safety & Compliance'
            },
            {
                'username': 'training.coordinator',
                'password': 'safety123',
                'first_name': 'Meera',
                'last_name': 'Nair',
                'email': 'meera.nair@marelli.com',
                'employee_id': 'SAF002',
                'plant': 'Main Plant',
                'unit': 'SAFETY TRAINING',
                'department': 'Training & Development'
            },
            {
                'username': 'operator.one',
                'password': 'safety123',
                'first_name': 'Vikram',
                'last_name': 'Singh',
                'email': 'vikram.singh@marelli.com',
                'employee_id': 'OPR001',
                'plant': 'Production Plant',
                'unit': 'SAFETY TRAINING',
                'department': 'Operations'
            },
            {
                'username': 'operator.two',
                'password': 'safety123',
                'first_name': 'Kavita',
                'last_name': 'Desai',
                'email': 'kavita.desai@marelli.com',
                'employee_id': 'OPR002',
                'plant': 'Production Plant',
                'unit': 'SAFETY TRAINING',
                'department': 'Operations'
            },
            {
                'username': 'maintenance.tech',
                'password': 'safety123',
                'first_name': 'Suresh',
                'last_name': 'Kumar',
                'email': 'suresh.kumar@marelli.com',
                'employee_id': 'MNT001',
                'plant': 'Main Plant',
                'unit': 'SAFETY TRAINING',
                'department': 'Maintenance'
            }
        ]
        
        for user_data in users_data:
            user = User.objects.create_user(
                username=user_data['username'],
                password=user_data['password'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                email=user_data['email']
            )
            
            EmployeeProfile.objects.create(
                user=user,
                employee_id=user_data['employee_id'],
                plant=user_data['plant'],
                unit=user_data['unit'],
                department=user_data['department']
            )
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(users_data)} training users'))
    
    def print_summary(self):
        """Print summary of loaded data"""
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('✅ SAFETY TRAINING DATA LOADED SUCCESSFULLY!'))
        self.stdout.write('='*70)
        
        self.stdout.write('\n📊 DATA SUMMARY:')
        self.stdout.write(f'  📦 Units: {Unit.objects.count()}')
        self.stdout.write(f'  🏭 Safety Lines: {Line.objects.count()}')
        self.stdout.write(f'  ⚠️  Safety Modules: {Operation.objects.count()}')
        self.stdout.write(f'  🎥 Training Videos: {TrainingVideo.objects.count()}')
        self.stdout.write(f'  📝 MCQ Tests: {MCQTest.objects.count()}')
        self.stdout.write(f'  ❓ Total Questions: {Question.objects.count()}')
        self.stdout.write(f'  👥 Training Users: {EmployeeProfile.objects.count()}')
        
        self.stdout.write('\n🎯 SAFETY MODULES CREATED:')
        self.stdout.write('  1. SAF-001: Near Miss - Helmet Safety (5 questions)')
        self.stdout.write('  2. SAF-002: Lab Entry Protocol (6 questions)')
        self.stdout.write('  3. SAF-003: Rigging & Lifting Safety (7 questions)')
        self.stdout.write('  4. SAF-004: Mobile Scaffolding Safety (6 questions)')
        self.stdout.write('  5. SAF-005: Good Housekeeping (5 questions)')
        self.stdout.write('  6. SAF-006: Vehicular Safety (7 questions)')
        
        self.stdout.write('\n👤 SAMPLE LOGIN CREDENTIALS:')
        self.stdout.write('  All passwords: safety123')
        self.stdout.write('  ─────────────────────────────────────────')
        self.stdout.write('  Username: safety.officer   | Arun Verma')
        self.stdout.write('  Username: training.coordinator | Meera Nair')
        self.stdout.write('  Username: operator.one     | Vikram Singh')
        self.stdout.write('  Username: operator.two     | Kavita Desai')
        self.stdout.write('  Username: maintenance.tech | Suresh Kumar')
        
        self.stdout.write('\n📹 UPLOAD YOUR SAFETY VIDEOS:')
        self.stdout.write('  1. Login to admin: http://localhost:8000/admin/')
        self.stdout.write('  2. Go to: Process DOJO → Training videos')
        self.stdout.write('  3. Click on each video module')
        self.stdout.write('  4. Upload your corresponding video file:')
        self.stdout.write('     • Animated Safety Training_ Near Miss - Helmet')
        self.stdout.write('     • Lab entry protocol (abridged)')
        self.stdout.write('     • Rigging & Lifting Safety training')
        self.stdout.write('     • Improper Mobile Scaffolding')
        self.stdout.write('     • Good housekeeping means safe workplace')
        self.stdout.write('     • On-premises vehicular safety')
        self.stdout.write('  5. Save each video')
        
        self.stdout.write('\n🎓 TESTING THE SYSTEM:')
        self.stdout.write('  1. Login with any user credentials')
        self.stdout.write('  2. Navigate: SAFETY TRAINING → Select Line → Select Module')
        self.stdout.write('  3. Watch safety video (after upload)')
        self.stdout.write('  4. Take MCQ test (high passing scores: 75-85%)')
        self.stdout.write('  5. Review results and explanations')
        
        self.stdout.write('\n⚠️  IMPORTANT NOTES:')
        self.stdout.write('  • Video files are placeholders - UPLOAD YOUR VIDEOS')
        self.stdout.write('  • High passing scores (75-85%) for safety compliance')
        self.stdout.write('  • 5 modules marked as CTQ (Critical to Quality)')
        self.stdout.write('  • All MCQs have detailed explanations')
        self.stdout.write('  • Users must complete videos to take tests')
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('🎉 READY FOR SAFETY TRAINING!'))
        self.stdout.write('='*70 + '\n')