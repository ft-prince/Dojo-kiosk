"""
Process DOJO - URL Configuration
Clean routing for training kiosk application
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import biometric_views

app_name = 'process_dojo'

urlpatterns = [
    # ========================================================================
    # BIOMETRIC AUTHENTICATION
    # ========================================================================
    path('biometric/login/', biometric_views.biometric_login_view, name='biometric_login'),
    path('biometric/authenticate/', biometric_views.biometric_authenticate, name='biometric_authenticate'),
    path('biometric/logout/', biometric_views.biometric_logout_view, name='biometric_logout'),
    path('biometric/device-status/', biometric_views.biometric_device_status, name='biometric_device_status'),
    
    # ========================================================================
    # BIOMETRIC ENROLLMENT (Admin Only)
    # ========================================================================
    path('biometric/enrollment/', biometric_views.biometric_enrollment_list, name='biometric_enrollment_list'),
    path('biometric/enrollment/<str:employee_id>/', biometric_views.biometric_enrollment_form, name='biometric_enrollment_form'),
    path('biometric/enroll/save/', biometric_views.biometric_enroll_save, name='biometric_enroll_save'),
    path('biometric/delete/', biometric_views.biometric_delete, name='biometric_delete'),

    
    
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
    path('login/', auth_views.LoginView.as_view(
        template_name='process_dojo/login.html'
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        next_page='process_dojo:login'
    ), name='logout'),
    
    # ========================================================================
    # MAIN DASHBOARD
    # ========================================================================
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard_alt'),
    
    # ========================================================================
    # TRAINING HIERARCHY NAVIGATION
    # ========================================================================
    path('unit/<int:pk>/', views.UnitDetailView.as_view(), name='unit_detail'),
    path('line/<int:pk>/', views.LineDetailView.as_view(), name='line_detail'),
    path('operation/<int:pk>/', views.OperationDetailView.as_view(), name='operation_detail'),
    
    # ========================================================================
    # VIDEO TRAINING
    # ========================================================================
    path('video/<int:pk>/', views.VideoDetailView.as_view(), name='video_detail'),
    path('video/<int:video_id>/update-progress/', views.update_video_progress, name='update_video_progress'),
    
    # ========================================================================
    # MCQ TESTING
    # ========================================================================
    path('test/start/<int:video_id>/', views.StartTestView.as_view(), name='start_test'),
    path('test/<int:attempt_id>/', views.TestPageView.as_view(), name='test_page'),
    path('test/autosave/', views.autosave_answer, name='autosave_answer'),
    path('test/submit/<int:attempt_id>/', views.SubmitTestView.as_view(), name='submit_test'),
    path('test/result/<int:attempt_id>/', views.ResultPageView.as_view(), name='result_page'),
    
    # ========================================================================
    # REPORTS
    # ========================================================================
    path('reports/videos/', views.VideoCompletionReportView.as_view(), name='video_report'),
    path('reports/tests/', views.TestAttemptReportView.as_view(), name='test_report'),
    path('reports/logins/', views.LoginSessionReportView.as_view(), name='login_report'),
    path('reports/plant/', views.PlantReportView.as_view(), name='plant_report'),
    path('reports/employee/', views.EmployeeReportView.as_view(), name='employee_report'),
        path('reports/test-attempts-detailed/',  # NEW
         views.TestAttemptDetailedReportView.as_view(), 
         name='test_attempt_detailed_report'),

    path('reports/user-test-history/',  # NEW
         views.UserTestHistoryReportView.as_view(), 
         name='user_test_history_report'),

]