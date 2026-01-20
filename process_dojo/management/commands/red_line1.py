"""
Django Management Command to Add RED LINE OP-125 Training Data
Usage: python manage.py add_red_line_training
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Add RED LINE OP-125 training structure and MCQ test'

    def handle(self, *args, **options):
        from process_dojo.models import Unit, Line, Operation, TrainingVideo, MCQTest, Question
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('RED LINE OP-125 TRAINING DATA IMPORT'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        with transaction.atomic():
            # STEP 1: Create structure
            self.stdout.write(self.style.SUCCESS('STEP 1: Creating Training Structure'))
            self.stdout.write('='*70)
            
            unit, created = Unit.objects.get_or_create(
                name="Unit-3",
                defaults={'description': 'Production Unit 3', 'is_active': True}
            )
            self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Found'} Unit: {unit.name}")
            
            line, created = Line.objects.get_or_create(
                unit=unit,
                name="RED LINE",
                defaults={'description': 'RED LINE - Clutch piston assembly', 'is_active': True}
            )
            self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Found'} Line: {line.name}")
            
            operation, created = Operation.objects.get_or_create(
                line=line,
                name="OP-125 RED Line (CTQ)",
                defaults={
                    'operation_code': 'OP-125',
                    'description': 'Clutch piston assembly',
                    'is_ctq_station': True,
                    'is_active': True,
                    'order': 125
                }
            )
            self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Found'} Operation: {operation.name}")
            self.stdout.write(f"📍 Path: {unit.name} → {line.name} → {operation.name}\n")
            
            # STEP 2: Create training video
            self.stdout.write(self.style.SUCCESS('STEP 2: Creating Training Video'))
            self.stdout.write('='*70)
            
            video, created = TrainingVideo.objects.get_or_create(
                operation=operation,
                title="OP-125 Piston Assembly Training",
                defaults={
                    'description': 'Training video for OP-125 Clutch piston assembly operation',
                    'duration_seconds': 0,
                    'has_voice': True,
                    'has_callouts': True,
                    'is_active': True,
                    'order': 1
                }
            )
            self.stdout.write(f"{'✅ Created' if created else 'ℹ️  Found'} Video: {video.title}\n")
            
            # STEP 3: Create MCQ test
            self.stdout.write(self.style.SUCCESS('STEP 3: Creating MCQ Test'))
            self.stdout.write('='*70)
            
            # Delete existing test if exists
            existing_count = MCQTest.objects.filter(video=video).count()
            if existing_count > 0:
                MCQTest.objects.filter(video=video).delete()
                self.stdout.write(self.style.WARNING(f'⚠️  Deleted {existing_count} existing test(s)'))
            
            mcq_test = MCQTest.objects.create(
                video=video,
                title="OP-125 Piston Assembly - Level 3 Test",
                description="Training evaluation test for OP-125 operation",
                passing_score=70,
                time_limit_minutes=30,
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Created MCQ Test: {mcq_test.title}"))
            self.stdout.write(f"   Passing Score: {mcq_test.passing_score}%")
            self.stdout.write(f"   Time Limit: {mcq_test.time_limit_minutes} minutes\n")
            
            # STEP 4: Add questions
            self.stdout.write(self.style.SUCCESS('STEP 4: Adding Questions'))
            self.stdout.write('='*70)
            
            questions_data = [
                {
                    'number': 1,
                    'question': 'How many SAE parts of op-125?',
                    'option_a': '1',
                    'option_b': '2',
                    'option_c': '3',
                    'option_d': '4',
                    'correct': 'B'
                },
                {
                    'number': 2,
                    'question': 'What is frequency of performing SAE cycle at op-125?',
                    'option_a': 'Every 1 Hour',
                    'option_b': 'Every 4 hour',
                    'option_c': 'Start of shift',
                    'option_d': 'Start of day',
                    'correct': 'D'
                },
                {
                    'number': 3,
                    'question': 'What do you meant by EWIS?',
                    'option_a': 'elementary Work Instruction Sheet',
                    'option_b': 'Essential Work Instruction Sheet',
                    'option_c': 'elementary Work Indication Sheet',
                    'option_d': 'Essential Work Indication Sheet',
                    'correct': 'A'
                },
                {
                    'number': 4,
                    'question': 'How many operator need to run op-125 in one shift?',
                    'option_a': '1',
                    'option_b': '2',
                    'option_c': '3',
                    'option_d': 'Non of these',
                    'correct': 'A'
                },
                {
                    'number': 5,
                    'question': 'What is full form of CTQ?',
                    'option_a': 'Class to quality',
                    'option_b': 'Close to quality',
                    'option_c': 'Critical to quality',
                    'option_d': 'Clone to quality',
                    'correct': 'C'
                },
                {
                    'number': 6,
                    'question': 'Which type oil are using for lubrication?',
                    'option_a': 'Drocerra Oil',
                    'option_b': 'Petronus oil',
                    'option_c': 'Hydraulic oil',
                    'option_d': 'None of these',
                    'correct': 'A'
                },
                {
                    'number': 7,
                    'question': 'What is full form of OPL?',
                    'option_a': 'One Point Lesson',
                    'option_b': 'One Point Learning',
                    'option_c': 'Only person learning',
                    'option_d': 'Only person lesson',
                    'correct': 'A'
                },
                {
                    'number': 8,
                    'question': 'What is target of op-125 in a single shift?',
                    'option_a': '175',
                    'option_b': '180',
                    'option_c': '185',
                    'option_d': '190',
                    'correct': 'C'
                },
                {
                    'number': 9,
                    'question': 'What is the full form of HMI',
                    'option_a': 'human manpower in charge',
                    'option_b': 'high machine instruction',
                    'option_c': 'human and machine to interact',
                    'option_d': 'NONE',
                    'correct': 'C'
                },
                {
                    'number': 10,
                    'question': 'Which tool using for guide bowden wire during CP insertion in BP?',
                    'option_a': 'Pnemutic gun',
                    'option_b': 'Ogiva',
                    'option_c': 'Seeger Plier',
                    'option_d': 'Oring insertion tool',
                    'correct': 'B'
                }
            ]
            
            for q_data in questions_data:
                question = Question.objects.create(
                    test=mcq_test,
                    question_text=q_data['question'],
                    option_a=q_data['option_a'],
                    option_b=q_data['option_b'],
                    option_c=q_data['option_c'],
                    option_d=q_data['option_d'],
                    correct_answer=q_data['correct'],
                    marks=1,
                    ordering=q_data['number']
                )
                self.stdout.write(f"   ✅ Q{q_data['number']}: {q_data['question'][:50]}... (Answer: {q_data['correct']})")
            
            # Summary
            self.stdout.write(self.style.SUCCESS('\n' + '='*70))
            self.stdout.write(self.style.SUCCESS('✅ IMPORT COMPLETED SUCCESSFULLY!'))
            self.stdout.write(self.style.SUCCESS('='*70))
            self.stdout.write('📊 Summary:')
            self.stdout.write(f"   • Operation: {operation.name}")
            self.stdout.write(f"   • Training Video: {video.title}")
            self.stdout.write(f"   • MCQ Test: {mcq_test.title}")
            self.stdout.write(f"   • Questions: {mcq_test.questions.count()}")
            self.stdout.write(f"   • Total Marks: {mcq_test.get_total_marks()}")
            self.stdout.write(self.style.SUCCESS('='*70 + '\n'))