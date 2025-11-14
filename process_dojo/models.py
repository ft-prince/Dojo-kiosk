"""
Process DOJO - Django Models
Offline training kiosk with video-based learning and MCQ testing
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class EmployeeProfile(models.Model):
    """Extended user profile for employees with organizational details"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    employee_id = models.CharField(max_length=50, unique=True, db_index=True)
    plant = models.CharField(max_length=100)
    unit = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    biometric_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['employee_id']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['plant', 'unit']),
        ]
    
    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"


class Unit(models.Model):
    """Top level organizational unit (ELS, AMT, UNIT-3, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Line(models.Model):
    """Production line within a unit (RED LINE, TATA LINE, MAHINDRA LINE, etc.)"""
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='lines')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['unit', 'name']
        unique_together = ['unit', 'name']
        indexes = [
            models.Index(fields=['unit', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.unit.name} - {self.name}"


class Operation(models.Model):
    """Specific operation on a line (OP-100 PLUGGING, OP-123 OPV, etc.)"""
    line = models.ForeignKey(Line, on_delete=models.CASCADE, related_name='operations')
    name = models.CharField(max_length=100)
    operation_code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_ctq_station = models.BooleanField(default=False, help_text="Critical to Quality station")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['line', 'order', 'name']
        unique_together = ['line', 'name']
        indexes = [
            models.Index(fields=['line', 'is_active']),
            models.Index(fields=['is_ctq_station']),
        ]
    
    def __str__(self):
        return f"{self.line.name} - {self.name}"


class TrainingVideo(models.Model):
    """Training video for an operation with support for voice/callouts"""
    operation = models.ForeignKey(Operation, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to='training_videos/%Y/%m/')
    thumbnail = models.ImageField(upload_to='video_thumbnails/', blank=True, null=True)
    duration_seconds = models.IntegerField(default=0, help_text="Video duration in seconds")
    has_voice = models.BooleanField(default=True)
    has_callouts = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['operation', 'order', 'title']
        indexes = [
            models.Index(fields=['operation', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.operation.name} - {self.title}"


class VideoCompletion(models.Model):
    """Track video watching progress and completion status"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_completions')
    video = models.ForeignKey(TrainingVideo, on_delete=models.CASCADE, related_name='completions')
    completion_percentage = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    is_completed = models.BooleanField(default=False)
    access_count = models.IntegerField(default=0)
    last_watched_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'video']
        ordering = ['-last_watched_at']
        indexes = [
            models.Index(fields=['user', 'is_completed']),
            models.Index(fields=['video', 'is_completed']),
            models.Index(fields=['-last_watched_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.video.title} ({self.completion_percentage}%)"
    
    def mark_access(self):
        """Increment access count"""
        self.access_count += 1
        self.save(update_fields=['access_count', 'last_watched_at'])
    
    def update_progress(self, percentage):
        """Update completion percentage and mark as completed if 100%"""
        self.completion_percentage = min(percentage, 100.0)
        if self.completion_percentage >= 100.0:
            self.is_completed = True
        self.save(update_fields=['completion_percentage', 'is_completed', 'last_watched_at'])


class MCQTest(models.Model):
    """MCQ test associated with a training video"""
    video = models.OneToOneField(TrainingVideo, on_delete=models.CASCADE, related_name='mcq_test')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    passing_score = models.IntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Passing percentage"
    )
    time_limit_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Time limit in minutes"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['video']
    
    def __str__(self):
        return f"Test: {self.title}"
    
    def get_total_marks(self):
        """Calculate total marks for the test"""
        return self.questions.aggregate(total=models.Sum('marks'))['total'] or 0


class Question(models.Model):
    """MCQ question with 4 options"""
    OPTION_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ]
    
    test = models.ForeignKey(MCQTest, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    correct_answer = models.CharField(max_length=1, choices=OPTION_CHOICES)
    marks = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    ordering = models.IntegerField(default=0, help_text="Question order in test")
    explanation = models.TextField(blank=True, help_text="Explanation for correct answer")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['test', 'ordering', 'id']
        indexes = [
            models.Index(fields=['test', 'ordering']),
        ]
    
    def __str__(self):
        return f"Q{self.ordering}: {self.question_text[:50]}"
    
    def get_options(self):
        """Return dictionary of all options"""
        return {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d,
        }


class TestAttempt(models.Model):
    """Track individual test attempts with auto-save support"""
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey(MCQTest, on_delete=models.CASCADE, related_name='attempts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])
    correct_answers = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    passed = models.BooleanField(default=False)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_saved_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['test', 'status']),
            models.Index(fields=['-started_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.test.title} ({self.status})"
    
    def calculate_score(self):
        """Calculate score based on saved answers"""
        total_marks = 0
        earned_marks = 0
        correct_count = 0
        
        for question in self.test.questions.all():
            total_marks += question.marks
            try:
                saved_answer = self.saved_answers.get(question=question)
                if saved_answer.is_correct:
                    earned_marks += question.marks
                    correct_count += 1
            except SavedAnswer.DoesNotExist:
                pass
        
        self.total_questions = self.test.questions.count()
        self.correct_answers = correct_count
        self.score = (earned_marks / total_marks * 100) if total_marks > 0 else 0
        self.passed = self.score >= self.test.passing_score
        return self.score
    
    def complete(self):
        """Mark attempt as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.calculate_score()
        self.save()


class SavedAnswer(models.Model):
    """Auto-saved answer for each question in a test attempt"""
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='saved_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='saved_answers')
    selected_option = models.CharField(max_length=1, choices=Question.OPTION_CHOICES, blank=True)
    is_correct = models.BooleanField(default=False)
    saved_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['attempt', 'question']
        indexes = [
            models.Index(fields=['attempt', 'question']),
        ]
    
    def __str__(self):
        return f"{self.attempt.user.username} - Q{self.question.ordering} - {self.selected_option}"
    
    def save(self, *args, **kwargs):
        """Automatically check if answer is correct"""
        if self.selected_option:
            self.is_correct = (self.selected_option == self.question.correct_answer)
        super().save(*args, **kwargs)


class LoginSession(models.Model):
    """Track user login/logout sessions for reporting"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_sessions')
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    session_duration_minutes = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', '-login_time']),
            models.Index(fields=['-login_time']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time.strftime('%Y-%m-%d %H:%M')}"
    
    def calculate_duration(self):
        """Calculate session duration in minutes"""
        if self.logout_time:
            duration = (self.logout_time - self.login_time).total_seconds() / 60
            self.session_duration_minutes = int(duration)
            self.save(update_fields=['session_duration_minutes'])