"""
Process DOJO - Admin Configuration
Django admin interface for managing training content and viewing reports
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import (
    EmployeeProfile, Unit, Line, Operation, TrainingVideo,
    VideoCompletion, MCQTest, Question, TestAttempt,
    SavedAnswer, LoginSession
)


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'user_full_name', 'plant', 'unit', 'department', 'created_at']
    list_filter = ['plant', 'unit', 'department', 'created_at']
    search_fields = ['employee_id', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'employee_id', 'biometric_id')
        }),
        ('Organizational Details', {
            'fields': ('plant', 'unit', 'department')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_full_name.short_description = 'Name'


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'line_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    def line_count(self, obj):
        return obj.lines.count()
    line_count.short_description = 'Lines'


@admin.register(Line)
class LineAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'is_active', 'operation_count', 'created_at']
    list_filter = ['unit', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'unit__name']
    readonly_fields = ['created_at']
    
    def operation_count(self, obj):
        return obj.operations.count()
    operation_count.short_description = 'Operations'


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ['name', 'operation_code', 'line', 'is_ctq_station', 'is_active', 'order', 'video_count']
    list_filter = ['line__unit', 'line', 'is_ctq_station', 'is_active']
    search_fields = ['name', 'operation_code', 'description']
    readonly_fields = ['created_at']
    list_editable = ['order']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('line', 'name', 'operation_code', 'description')
        }),
        ('Classification', {
            'fields': ('is_ctq_station', 'is_active', 'order')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def video_count(self, obj):
        return obj.videos.count()
    video_count.short_description = 'Videos'


@admin.register(TrainingVideo)
class TrainingVideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'operation', 'duration_display', 'has_voice', 'has_callouts', 'is_active', 'completion_count']
    list_filter = ['operation__line__unit', 'operation__line', 'is_active', 'has_voice', 'has_callouts']
    search_fields = ['title', 'description', 'operation__name']
    readonly_fields = ['created_at', 'updated_at', 'preview_thumbnail']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('operation', 'title', 'description', 'order')
        }),
        ('Media Files', {
            'fields': ('video_file', 'thumbnail', 'preview_thumbnail', 'duration_seconds')
        }),
        ('Features', {
            'fields': ('has_voice', 'has_callouts', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def duration_display(self, obj):
        minutes = obj.duration_seconds // 60
        seconds = obj.duration_seconds % 60
        return f"{minutes}:{seconds:02d}"
    duration_display.short_description = 'Duration'
    
    def completion_count(self, obj):
        return obj.completions.filter(is_completed=True).count()
    completion_count.short_description = 'Completions'
    
    def preview_thumbnail(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.thumbnail.url)
        return "No thumbnail"
    preview_thumbnail.short_description = 'Preview'


@admin.register(VideoCompletion)
class VideoCompletionAdmin(admin.ModelAdmin):
    list_display = ['user', 'video', 'completion_percentage', 'is_completed', 'access_count', 'last_watched_at']
    list_filter = ['is_completed', 'video__operation__line__unit', 'last_watched_at']
    search_fields = ['user__username', 'user__employee_profile__employee_id', 'video__title']
    readonly_fields = ['created_at', 'last_watched_at']
    date_hierarchy = 'last_watched_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user__employee_profile',
            'video__operation__line__unit'
        )


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['ordering', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'marks']


@admin.register(MCQTest)
class MCQTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'video', 'passing_score', 'time_limit_minutes', 'question_count', 'is_active', 'attempt_count']
    list_filter = ['is_active', 'video__operation__line__unit']
    search_fields = ['title', 'description', 'video__title']
    readonly_fields = ['created_at', 'updated_at', 'total_marks']
    inlines = [QuestionInline]
    
    fieldsets = (
        ('Test Information', {
            'fields': ('video', 'title', 'description')
        }),
        ('Test Settings', {
            'fields': ('passing_score', 'time_limit_minutes', 'is_active')
        }),
        ('Statistics', {
            'fields': ('total_marks',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'
    
    def attempt_count(self, obj):
        return obj.attempts.count()
    attempt_count.short_description = 'Attempts'
    
    def total_marks(self, obj):
        return obj.get_total_marks()
    total_marks.short_description = 'Total Marks'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['short_question', 'test', 'correct_answer', 'marks', 'ordering']
    list_filter = ['test__video__operation__line__unit', 'test', 'correct_answer']
    search_fields = ['question_text', 'test__title']
    list_editable = ['ordering']
    
    fieldsets = (
        ('Question', {
            'fields': ('test', 'question_text', 'ordering', 'marks')
        }),
        ('Options', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d')
        }),
        ('Answer', {
            'fields': ('correct_answer', 'explanation')
        }),
    )
    
    def short_question(self, obj):
        return obj.question_text[:100] + '...' if len(obj.question_text) > 100 else obj.question_text
    short_question.short_description = 'Question'


class SavedAnswerInline(admin.TabularInline):
    model = SavedAnswer
    extra = 0
    readonly_fields = ['question', 'selected_option', 'is_correct', 'saved_at']
    can_delete = False


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'test', 'status', 'score', 'passed', 'started_at', 'completed_at']
    list_filter = ['status', 'passed', 'test__video__operation__line__unit', 'started_at']
    search_fields = ['user__username', 'user__employee_profile__employee_id', 'test__title']
    readonly_fields = ['started_at', 'completed_at', 'last_saved_at']
    date_hierarchy = 'started_at'
    inlines = [SavedAnswerInline]
    
    fieldsets = (
        ('Attempt Information', {
            'fields': ('user', 'test', 'status')
        }),
        ('Results', {
            'fields': ('score', 'correct_answers', 'total_questions', 'passed')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at', 'last_saved_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user__employee_profile',
            'test__video__operation'
        )


@admin.register(SavedAnswer)
class SavedAnswerAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question_short', 'selected_option', 'is_correct', 'saved_at']
    list_filter = ['is_correct', 'selected_option', 'saved_at']
    search_fields = ['attempt__user__username', 'question__question_text']
    readonly_fields = ['saved_at']
    
    def question_short(self, obj):
        return obj.question.question_text[:50] + '...' if len(obj.question.question_text) > 50 else obj.question.question_text
    question_short.short_description = 'Question'


@admin.register(LoginSession)
class LoginSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee_id_display', 'login_time', 'logout_time', 'session_duration_minutes']
    list_filter = ['login_time', 'logout_time']
    search_fields = ['user__username', 'user__employee_profile__employee_id']
    readonly_fields = ['login_time', 'logout_time', 'session_duration_minutes']
    date_hierarchy = 'login_time'
    
    def employee_id_display(self, obj):
        try:
            return obj.user.employee_profile.employee_id
        except:
            return 'N/A'
    employee_id_display.short_description = 'Employee ID'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user__employee_profile')


# Customize admin site header
admin.site.site_header = "Process DOJO Administration"
admin.site.site_title = "Process DOJO Admin"
admin.site.index_title = "Training Management System"