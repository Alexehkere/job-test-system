from django.urls import path
from django.contrib.auth.views import LogoutView
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('company/register/', views.company_register, name='company_register'),
    path('register/applicant/', views.register_applicant, name='register_applicant'),
    path('register/employer/', views.register_employer, name='register_employer'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),  # Оставляем как есть
    path('company/dashboard/', views.company_dashboard, name='company_dashboard'),
    path('employer/dashboard/', views.employer_dashboard, name='employer_dashboard'),
    path('employer/tests/create/', views.create_test, name='create_test'),
    path('employer/tests/<int:test_id>/edit/', views.edit_test, name='edit_test'),
    path('employer/tests/<int:question_id>/edit_question/', views.edit_question, name='edit_question'),
    path('employer/tests/<int:question_id>/delete_question/', views.delete_question, name='delete_question'),
    path('employer/tests/<int:test_id>/delete/', views.delete_test, name='delete_test'),
    path('employer/tests/<int:test_id>/create_question/', views.create_question, name='create_question'),
    path('employer/tests/<int:test_id>/assign/', views.assign_test, name='assign_test'),
    path('applicant/dashboard/', views.applicant_dashboard, name='applicant_dashboard'),
    path('applicant/test/<int:assignment_id>/', views.take_test, name='take_test'),
    path('applicant/test/<int:assignment_id>/result/', views.test_result, name='test_result'),
    path('employer/reports/', views.employer_reports, name='employer_reports'),
    path('register/user/', views.user_registration, name='user_registration'),
    path('admin/companies/', views.company_approval_list, name='company_approval_list'),
    path('invite/applicant/', views.invite_applicant, name='invite_applicant'),
    path('manage/users/', views.manage_users, name='manage_users'),
    path('applicant/', RedirectView.as_view(url='/applicant/dashboard/', permanent=True)),
]