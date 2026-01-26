"""
Process DOJO - Django Views
Handles operator training flow, video tracking, MCQ testing, and reporting
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.views import View as DjangoView
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
import csv
from datetime import datetime, timedelta

from .models import (
    Unit, Line, Operation, TrainingVideo, VideoCompletion,
    MCQTest, Question, TestAttempt, SavedAnswer, LoginSession,
    EmployeeProfile
)


# ============================================================================
# OPERATOR TRAINING FLOW
# ============================================================================

class DashboardView(LoginRequiredMixin, ListView):
    """Main dashboard showing training hierarchy: Units → Lines → Operations"""
    template_name = 'process_dojo/dashboard.html'
    context_object_name = 'units'
    
    def get_queryset(self):
        return Unit.objects.filter(is_active=True).prefetch_related(
            'lines__operations__videos'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user statistics
        context['total_videos_completed'] = VideoCompletion.objects.filter(
            user=user, is_completed=True
        ).count()
        
        context['total_tests_passed'] = TestAttempt.objects.filter(
            user=user, status='completed', passed=True
        ).count()
        
        context['in_progress_attempts'] = TestAttempt.objects.filter(
            user=user, status='in_progress'
        ).count()
        
        # Recent activity
        context['recent_completions'] = VideoCompletion.objects.filter(
            user=user
        ).select_related('video__operation__line__unit').order_by('-last_watched_at')[:5]
        
        return context


class UnitDetailView(LoginRequiredMixin, DetailView):
    """Display lines within a selected unit"""
    model = Unit
    template_name = 'process_dojo/unit_detail.html'
    context_object_name = 'unit'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lines'] = self.object.lines.filter(is_active=True).prefetch_related('operations')
        return context


class LineDetailView(LoginRequiredMixin, DetailView):
    """Display operations within a selected line"""
    model = Line
    template_name = 'process_dojo/line_detail.html'
    context_object_name = 'line'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['operations'] = self.object.operations.filter(
            is_active=True
        ).prefetch_related('videos')
        return context


class OperationDetailView(LoginRequiredMixin, DetailView):
    """Display videos for a selected operation"""
    model = Operation
    template_name = 'process_dojo/operation_detail.html'
    context_object_name = 'operation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        videos = self.object.videos.filter(is_active=True)
        
        # Annotate with user's completion status
        video_data = []
        for video in videos:
            try:
                completion = VideoCompletion.objects.get(
                    user=self.request.user, video=video
                )
                video_data.append({
                    'video': video,
                    'completion': completion,
                })
            except VideoCompletion.DoesNotExist:
                video_data.append({
                    'video': video,
                    'completion': None,
                })
        
        context['video_data'] = video_data
        return context


class VideoDetailView(LoginRequiredMixin, DetailView):
    """Play training video and track progress"""
    model = TrainingVideo
    template_name = 'process_dojo/video_detail.html'
    context_object_name = 'video'
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Get or create video completion record
        completion, created = VideoCompletion.objects.get_or_create(
            user=request.user,
            video=self.object,
        )
        
        # Increment access count
        completion.mark_access()
        
        context = self.get_context_data(object=self.object)
        context['completion'] = completion
        
        # Check if test is available
        try:
            context['mcq_test'] = self.object.mcq_test
        except MCQTest.DoesNotExist:
            context['mcq_test'] = None
        
        return self.render_to_response(context)


@login_required
@require_POST
def update_video_progress(request, video_id):
    """AJAX endpoint to update video completion percentage"""
    try:
        video = get_object_or_404(TrainingVideo, id=video_id)
        completion = get_object_or_404(
            VideoCompletion,
            user=request.user,
            video=video
        )
        
        percentage = float(request.POST.get('percentage', 0))
        completion.update_progress(percentage)
        
        return JsonResponse({
            'success': True,
            'percentage': completion.completion_percentage,
            'is_completed': completion.is_completed,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================================================
# MCQ TESTING FLOW
# ============================================================================

class StartTestView(LoginRequiredMixin, View):
    """Start or resume a test for a video"""
    
    def get(self, request, video_id):
        video = get_object_or_404(TrainingVideo, id=video_id)
        
        # Check if video is completed
        try:
            completion = VideoCompletion.objects.get(
                user=request.user,
                video=video
            )
            if not completion.is_completed:
                messages.warning(
                    request,
                    "Please complete watching the video before taking the test."
                )
                return redirect('process_dojo:video_detail', pk=video_id)
        except VideoCompletion.DoesNotExist:
            messages.error(
                request,
                "You must watch the video first before taking the test."
            )
            return redirect('process_dojo:video_detail', pk=video_id)
        
        # Check if test exists
        try:
            test = video.mcq_test
        except MCQTest.DoesNotExist:
            messages.error(request, "No test is available for this video.")
            return redirect('process_dojo:video_detail', pk=video_id)
        
        # Check for existing in-progress attempt
        existing_attempt = TestAttempt.objects.filter(
            user=request.user,
            test=test,
            status='in_progress'
        ).first()
        
        if existing_attempt:
            messages.info(request, "Resuming your previous test attempt.")
            return redirect('process_dojo:test_page', attempt_id=existing_attempt.id)
        
        # Create new attempt
        attempt = TestAttempt.objects.create(
            user=request.user,
            test=test,
            total_questions=test.questions.count()
        )
        
        messages.success(request, f"Test started: {test.title}")
        return redirect('process_dojo:test_page', attempt_id=attempt.id)


class TestPageView(LoginRequiredMixin, DetailView):
    """Display MCQ test with all questions"""
    model = TestAttempt
    template_name = 'process_dojo/test_page.html'
    context_object_name = 'attempt'
    pk_url_kwarg = 'attempt_id'
    
    def get_queryset(self):
        # Users can only access their own attempts
        return TestAttempt.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if test is already completed - redirect if so
        if self.object.status == 'completed':
            # Cannot redirect from get_context_data, handle in dispatch instead
            pass
        
        # Get all questions with saved answers
        questions = self.object.test.questions.all()
        question_data = []
        
        for question in questions:
            try:
                saved_answer = SavedAnswer.objects.get(
                    attempt=self.object,
                    question=question
                )
                selected = saved_answer.selected_option
            except SavedAnswer.DoesNotExist:
                selected = None
            
            question_data.append({
                'question': question,
                'selected_option': selected,
            })
        
        context['question_data'] = question_data
        context['test'] = self.object.test
        
        # Calculate time remaining
        elapsed = timezone.now() - self.object.started_at
        time_limit = timedelta(minutes=self.object.test.time_limit_minutes)
        remaining = time_limit - elapsed
        
        context['time_remaining_seconds'] = max(0, int(remaining.total_seconds()))
        context['time_expired'] = remaining.total_seconds() <= 0
        
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """Check if test is completed before rendering"""
        self.object = self.get_object()
        if self.object.status == 'completed':
            messages.info(request, "This test has already been completed.")
            return redirect('process_dojo:result_page', attempt_id=self.object.id)
        return super().dispatch(request, *args, **kwargs)


@login_required
@require_POST
def autosave_answer(request):
    """AJAX endpoint for auto-saving test answers"""
    try:
        attempt_id = request.POST.get('attempt_id')
        question_id = request.POST.get('question_id')
        selected_option = request.POST.get('selected_option')
        
        attempt = get_object_or_404(
            TestAttempt,
            id=attempt_id,
            user=request.user,
            status='in_progress'
        )
        
        question = get_object_or_404(Question, id=question_id, test=attempt.test)
        
        # Create or update saved answer
        saved_answer, created = SavedAnswer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={'selected_option': selected_option}
        )
        
        # Update attempt's last_saved_at
        attempt.save(update_fields=['last_saved_at'])
        
        return JsonResponse({
            'success': True,
            'is_correct': saved_answer.is_correct,
            'saved_at': saved_answer.saved_at.isoformat(),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


class SubmitTestView(LoginRequiredMixin, View):
    """Submit and evaluate test"""
    
    def post(self, request, attempt_id):
        attempt = get_object_or_404(
            TestAttempt,
            id=attempt_id,
            user=request.user,
            status='in_progress'
        )
        
        # Complete the attempt (calculates score automatically)
        attempt.complete()
        
        if attempt.passed:
            messages.success(
                request,
                f"Congratulations! You passed with {attempt.score:.1f}%"
            )
        else:
            messages.warning(
                request,
                f"You scored {attempt.score:.1f}%. Passing score is {attempt.test.passing_score}%. Please try again after reviewing the material."
            )
        
        return redirect('process_dojo:result_page', attempt_id=attempt.id)


class ResultPageView(LoginRequiredMixin, DetailView):
    """Display test results with answer comparison"""
    model = TestAttempt
    template_name = 'process_dojo/result_page.html'
    context_object_name = 'attempt'
    pk_url_kwarg = 'attempt_id'
    
    def get_queryset(self):
        return TestAttempt.objects.filter(
            user=self.request.user,
            status='completed'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all questions with user answers and correct answers
        questions = self.object.test.questions.all()
        results_data = []
        
        for question in questions:
            try:
                saved_answer = SavedAnswer.objects.get(
                    attempt=self.object,
                    question=question
                )
                user_answer = saved_answer.selected_option
                is_correct = saved_answer.is_correct
            except SavedAnswer.DoesNotExist:
                user_answer = None
                is_correct = False
            
            results_data.append({
                'question': question,
                'user_answer': user_answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'user_answer_text': question.get_options().get(user_answer, 'Not answered'),
                'correct_answer_text': question.get_options().get(question.correct_answer),
            })
        
        context['results_data'] = results_data
        context['percentage'] = self.object.score
        context['passed'] = self.object.passed
        
        return context


# ============================================================================
# REPORTING VIEWS
# ============================================================================

# ============================================================================
# REPORTING VIEWS WITH USERNAME AND ATTEMPT TRACKING
# ============================================================================

class VideoCompletionReportView(LoginRequiredMixin, View):
    """Export video completion report as CSV with username"""
    
    def get(self, request):
        # Get date range from query parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        queryset = VideoCompletion.objects.select_related(
            'user__employee_profile',
            'video__operation__line__unit'
        ).all()
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="video_completion_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Time', 'Username', 'Employee ID', 'Employee Name', 'Plant', 
            'Unit', 'Line', 'Operation', 'Video Title', 'Completion %', 'Completed',
            'Access Count', 'Last Watched'
        ])
        
        for completion in queryset:
            profile = completion.user.employee_profile
            writer.writerow([
                completion.created_at.strftime('%Y-%m-%d'),
                completion.created_at.strftime('%H:%M:%S'),
                completion.user.username,
                profile.employee_id,
                completion.user.get_full_name(),
                profile.plant,
                completion.video.operation.line.unit.name,
                completion.video.operation.line.name,
                completion.video.operation.name,
                completion.video.title,
                f"{completion.completion_percentage:.1f}",
                'Yes' if completion.is_completed else 'No',
                completion.access_count,
                completion.last_watched_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        return response


class TestAttemptReportView(LoginRequiredMixin, View):
    """Export test attempt report as CSV with username and attempt numbers"""
    
    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        queryset = TestAttempt.objects.select_related(
            'user__employee_profile',
            'test__video__operation__line__unit'
        ).filter(status='completed')
        
        if start_date:
            queryset = queryset.filter(started_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(started_at__lte=end_date)
        
        # Order by user, test, and started_at to calculate attempt numbers
        queryset = queryset.order_by('user', 'test', 'started_at')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="test_attempt_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Time', 'Username', 'Employee ID', 'Employee Name', 'Plant', 
            'Unit', 'Line', 'Operation', 'Test Title', 'Attempt Number', 
            'Score %', 'Correct Answers', 'Total Questions', 'Result', 
            'Duration (minutes)', 'Total Attempts for This Test'
        ])
        
        # Track attempt numbers per user per test
        attempt_tracker = {}
        
        for attempt in queryset:
            profile = attempt.user.employee_profile
            
            # Create unique key for user-test combination
            user_test_key = f"{attempt.user.id}_{attempt.test.id}"
            
            # Initialize or increment attempt number
            if user_test_key not in attempt_tracker:
                attempt_tracker[user_test_key] = 0
            attempt_tracker[user_test_key] += 1
            attempt_number = attempt_tracker[user_test_key]
            
            # Calculate total attempts for this user-test combination
            total_attempts = TestAttempt.objects.filter(
                user=attempt.user,
                test=attempt.test,
                status='completed'
            ).count()
            
            # Calculate duration
            duration = 0
            if attempt.completed_at:
                duration = int((attempt.completed_at - attempt.started_at).total_seconds() / 60)
            
            writer.writerow([
                attempt.started_at.strftime('%Y-%m-%d'),
                attempt.started_at.strftime('%H:%M:%S'),
                attempt.user.username,
                profile.employee_id,
                attempt.user.get_full_name(),
                profile.plant,
                attempt.test.video.operation.line.unit.name,
                attempt.test.video.operation.line.name,
                attempt.test.video.operation.name,
                attempt.test.title,
                f"Attempt {attempt_number}",
                f"{attempt.score:.1f}",
                attempt.correct_answers,
                attempt.total_questions,
                'Pass' if attempt.passed else 'Fail',
                duration,
                total_attempts,
            ])
        
        return response


class TestAttemptDetailedReportView(LoginRequiredMixin, View):
    """Detailed test attempt report grouped by user and test"""
    
    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        queryset = TestAttempt.objects.select_related(
            'user__employee_profile',
            'test__video__operation__line__unit'
        ).filter(status='completed')
        
        if start_date:
            queryset = queryset.filter(started_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(started_at__lte=end_date)
        
        queryset = queryset.order_by('user', 'test', 'started_at')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="test_attempt_detailed_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Employee ID', 'Employee Name', 'Plant', 'Unit',
            'Test Title', 'Attempt Number', 'Date', 'Time', 'Score %', 
            'Result', 'Correct/Total', 'Duration (min)', 
            'Best Score', 'Total Attempts', 'Pass Rate %'
        ])
        
        # Group attempts by user and test
        current_user_test = None
        attempts_list = []
        
        for attempt in queryset:
            user_test_key = f"{attempt.user.id}_{attempt.test.id}"
            
            if current_user_test != user_test_key:
                # Process previous group
                if attempts_list:
                    self._write_attempt_group(writer, attempts_list)
                
                # Start new group
                current_user_test = user_test_key
                attempts_list = [attempt]
            else:
                attempts_list.append(attempt)
        
        # Process last group
        if attempts_list:
            self._write_attempt_group(writer, attempts_list)
        
        return response
    
    def _write_attempt_group(self, writer, attempts_list):
        """Write a group of attempts for the same user and test"""
        if not attempts_list:
            return
        
        first_attempt = attempts_list[0]
        profile = first_attempt.user.employee_profile
        
        # Calculate statistics
        total_attempts = len(attempts_list)
        best_score = max(att.score for att in attempts_list)
        passed_count = sum(1 for att in attempts_list if att.passed)
        pass_rate = (passed_count / total_attempts * 100) if total_attempts > 0 else 0
        
        # Write each attempt
        for idx, attempt in enumerate(attempts_list, 1):
            duration = 0
            if attempt.completed_at:
                duration = int((attempt.completed_at - attempt.started_at).total_seconds() / 60)
            
            writer.writerow([
                attempt.user.username,
                profile.employee_id,
                attempt.user.get_full_name(),
                profile.plant,
                profile.unit if hasattr(profile, 'unit') else '',
                attempt.test.title,
                f"Attempt {idx}",
                attempt.started_at.strftime('%Y-%m-%d'),
                attempt.started_at.strftime('%H:%M:%S'),
                f"{attempt.score:.1f}",
                'Pass' if attempt.passed else 'Fail',
                f"{attempt.correct_answers}/{attempt.total_questions}",
                duration,
                f"{best_score:.1f}" if idx == 1 else '',  # Show only on first row
                total_attempts if idx == 1 else '',  # Show only on first row
                f"{pass_rate:.1f}" if idx == 1 else '',  # Show only on first row
            ])


class LoginSessionReportView(LoginRequiredMixin, View):
    """Export login session report as CSV with username"""
    
    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        queryset = LoginSession.objects.select_related(
            'user__employee_profile'
        ).all()
        
        if start_date:
            queryset = queryset.filter(login_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(login_time__lte=end_date)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="login_session_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Login Time', 'Logout Time', 'Username', 'Employee ID',
            'Employee Name', 'Plant', 'Unit', 'Duration (minutes)'
        ])
        
        for session in queryset:
            profile = session.user.employee_profile
            logout_time = session.logout_time.strftime('%H:%M:%S') if session.logout_time else 'Active'
            
            writer.writerow([
                session.login_time.strftime('%Y-%m-%d'),
                session.login_time.strftime('%H:%M:%S'),
                logout_time,
                session.user.username,
                profile.employee_id,
                session.user.get_full_name(),
                profile.plant,
                profile.unit,
                session.session_duration_minutes,
            ])
        
        return response


class PlantReportView(LoginRequiredMixin, View):
    """Consolidated plant-level report with username"""
    
    def get(self, request):
        plant = request.GET.get('plant')
        unit = request.GET.get('unit')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Build filter conditions
        filters = {}
        if start_date:
            filters['created_at__gte'] = start_date
        if end_date:
            filters['created_at__lte'] = end_date
        
        # Get employee profiles for filtering
        employee_filters = {}
        if plant:
            employee_filters['plant'] = plant
        if unit:
            employee_filters['unit'] = unit
        
        employee_ids = EmployeeProfile.objects.filter(
            **employee_filters
        ).values_list('user_id', flat=True)
        
        # Video completions
        video_completions = VideoCompletion.objects.filter(
            user_id__in=employee_ids,
            **filters
        ).select_related('user__employee_profile', 'video__operation')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="plant_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Report Type', 'Date', 'Username', 'Employee ID', 'Name', 
            'Plant', 'Unit', 'Details', 'Status', 'Score/Completion'
        ])
        
        for completion in video_completions:
            profile = completion.user.employee_profile
            writer.writerow([
                'Video Completion',
                completion.created_at.strftime('%Y-%m-%d'),
                completion.user.username,
                profile.employee_id,
                completion.user.get_full_name(),
                profile.plant,
                profile.unit,
                f"{completion.video.operation.name} - {completion.video.title}",
                'Completed' if completion.is_completed else 'In Progress',
                f"{completion.completion_percentage:.1f}%",
            ])
        
        return response


class EmployeeReportView(LoginRequiredMixin, View):
    """Individual employee training report with attempt tracking"""
    
    def get(self, request):
        employee_id = request.GET.get('employee_id')
        
        try:
            profile = EmployeeProfile.objects.select_related('user').get(
                employee_id=employee_id
            )
        except EmployeeProfile.DoesNotExist:
            messages.error(request, f"Employee {employee_id} not found.")
            return redirect('dashboard')
        
        user = profile.user
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="employee_{employee_id}_report.csv"'
        
        writer = csv.writer(response)
        
        # Header
        writer.writerow(['Employee Training Report'])
        writer.writerow(['Username:', user.username])
        writer.writerow(['Employee ID:', profile.employee_id])
        writer.writerow(['Name:', user.get_full_name()])
        writer.writerow(['Plant:', profile.plant])
        writer.writerow(['Unit:', profile.unit])
        writer.writerow(['Department:', profile.department])
        writer.writerow([])
        
        # Video completions
        writer.writerow(['VIDEO TRAINING PROGRESS'])
        writer.writerow(['Date', 'Operation', 'Video', 'Completion %', 'Status', 'Access Count'])
        
        completions = VideoCompletion.objects.filter(user=user).select_related(
            'video__operation__line__unit'
        ).order_by('-last_watched_at')
        
        for completion in completions:
            writer.writerow([
                completion.last_watched_at.strftime('%Y-%m-%d'),
                completion.video.operation.name,
                completion.video.title,
                f"{completion.completion_percentage:.1f}",
                'Completed' if completion.is_completed else 'In Progress',
                completion.access_count,
            ])
        
        writer.writerow([])
        
        # Test attempts with attempt numbers
        writer.writerow(['TEST RESULTS'])
        writer.writerow(['Test', 'Attempt #', 'Date', 'Score %', 'Result', 'Correct/Total', 'Duration (min)'])
        
        attempts = TestAttempt.objects.filter(
            user=user,
            status='completed'
        ).select_related('test__video__operation').order_by('test', 'started_at')
        
        # Track attempt numbers per test
        test_attempt_counter = {}
        
        for attempt in attempts:
            test_id = attempt.test.id
            if test_id not in test_attempt_counter:
                test_attempt_counter[test_id] = 0
            test_attempt_counter[test_id] += 1
            
            duration = 0
            if attempt.completed_at:
                duration = int((attempt.completed_at - attempt.started_at).total_seconds() / 60)
            
            writer.writerow([
                attempt.test.title,
                f"Attempt {test_attempt_counter[test_id]}",
                attempt.completed_at.strftime('%Y-%m-%d %H:%M') if attempt.completed_at else '',
                f"{attempt.score:.1f}",
                'Pass' if attempt.passed else 'Fail',
                f"{attempt.correct_answers}/{attempt.total_questions}",
                duration,
            ])
        
        writer.writerow([])
        
        # Test summary
        writer.writerow(['TEST SUMMARY'])
        writer.writerow(['Test Name', 'Total Attempts', 'Best Score', 'Latest Score', 'Pass Rate %'])
        
        # Group attempts by test
        from collections import defaultdict
        test_summary = defaultdict(list)
        
        for attempt in attempts:
            test_summary[attempt.test.id].append(attempt)
        
        for test_id, test_attempts in test_summary.items():
            test = test_attempts[0].test
            total = len(test_attempts)
            best = max(att.score for att in test_attempts)
            latest = test_attempts[-1].score
            passed = sum(1 for att in test_attempts if att.passed)
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            writer.writerow([
                test.title,
                total,
                f"{best:.1f}%",
                f"{latest:.1f}%",
                f"{pass_rate:.1f}%",
            ])
        
        return response


class UserTestHistoryReportView(LoginRequiredMixin, View):
    """Report showing all users and their test attempt history"""
    
    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        test_id = request.GET.get('test_id')
        
        queryset = TestAttempt.objects.select_related(
            'user__employee_profile',
            'test__video__operation'
        ).filter(status='completed')
        
        if start_date:
            queryset = queryset.filter(started_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(started_at__lte=end_date)
        if test_id:
            queryset = queryset.filter(test_id=test_id)
        
        queryset = queryset.order_by('user', 'test', 'started_at')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_test_history_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Employee ID', 'Employee Name', 'Test Title',
            'Attempt History', 'Total Attempts', 'Best Score', 'Average Score',
            'Pass Rate', 'First Attempt Date', 'Last Attempt Date'
        ])
        
        # Group by user and test
        from collections import defaultdict
        user_test_data = defaultdict(list)
        
        for attempt in queryset:
            key = (attempt.user.id, attempt.test.id)
            user_test_data[key].append(attempt)
        
        # Write summary for each user-test combination
        for (user_id, test_id), attempts in user_test_data.items():
            first_attempt = attempts[0]
            profile = first_attempt.user.employee_profile
            
            # Calculate statistics
            total = len(attempts)
            scores = [att.score for att in attempts]
            best_score = max(scores)
            avg_score = sum(scores) / len(scores)
            passed = sum(1 for att in attempts if att.passed)
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            # Create attempt history string
            attempt_history = ', '.join([
                f"#{i+1}: {att.score:.1f}% ({'Pass' if att.passed else 'Fail'})"
                for i, att in enumerate(attempts)
            ])
            
            writer.writerow([
                first_attempt.user.username,
                profile.employee_id,
                first_attempt.user.get_full_name(),
                first_attempt.test.title,
                attempt_history,
                total,
                f"{best_score:.1f}%",
                f"{avg_score:.1f}%",
                f"{pass_rate:.1f}%",
                attempts[0].started_at.strftime('%Y-%m-%d'),
                attempts[-1].started_at.strftime('%Y-%m-%d'),
            ])
        
        return response
