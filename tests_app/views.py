from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Test, Question, Option, TestAssignment, Answer, Category, Notification, CustomUser, Company, CompanyInvitation
from .forms import CompanyRegistrationForm, UserRegistrationForm, CompanyInvitationForm
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Avg
from django.db.models import Count, Q

def index(request):
    return redirect('login')

def company_register(request):
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.is_approved = False
            company.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                email=form.cleaned_data['contact_email'],
                role='admin',
                company=company,
                is_approved=False,
                first_name=form.cleaned_data.get('first_name', ''),
                last_name=form.cleaned_data.get('last_name', '')
            )
            login(request, user)
            messages.success(request, 'Спасибо за регистрацию! Ваша компания и аккаунт администратора ожидают одобрения.')
            return redirect('pending_approval')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = CompanyRegistrationForm()
    return render(request, 'company_register.html', {'form': form})

def register_applicant(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'applicant'
            user.company = form.cleaned_data['company']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.position = form.cleaned_data['position']  # Сохранение позиции
            user.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('applicant_dashboard')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = UserRegistrationForm(initial={'role': 'applicant'})
    return render(request, 'register_applicant.html', {'form': form})

def register_employer(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, initial={'role': 'employer'})
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'employer'
            user.first_name = form.cleaned_data.get('first_name', '')  # Опционально
            user.last_name = form.cleaned_data.get('last_name', '')    # Опционально
            user.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('employer_dashboard')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
            for error in form.errors.values():
                print(error)
    else:
        form = UserRegistrationForm(initial={'role': 'employer'})
    return render(request, 'register_employer.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                messages.error(request, 'Ваш аккаунт заблокирован.')
                return redirect('login')
            login(request, user)
            if user.role == 'employer' and user.is_approved:
                return redirect('employer_dashboard')
            elif user.role == 'admin':
                return redirect('manage_users')
            elif user.role == 'applicant':
                return redirect('applicant_dashboard')
            elif user.role == 'employer' and not user.is_approved:
                messages.warning(request, 'Ваша заявка на роль работодателя еще не одобрена. Ожидайте подтверждения.')
                return render(request, 'pending_approval.html')
            else:
                return redirect('index')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def company_dashboard(request):
    if request.user.role != 'admin' or not request.user.company or not request.user.is_active:
        messages.error(request, 'Доступ запрещён.')
        return redirect('login')

    company = request.user.company
    pending_employers = CustomUser.objects.filter(company=company, role='employer', is_approved=False)
    approved_employers = CustomUser.objects.filter(company=company, role='employer', is_approved=True, is_active=True)

    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        employer = get_object_or_404(CustomUser, id=user_id, company=company, role='employer')

        if action == 'approve_employer':
            employer.is_approved = True
            employer.save()
            Notification.objects.create(
                user=employer,
                message=f"Ваша заявка на роль работодателя в компании '{company.name}' одобрена."
            )
            messages.success(request, f"Работодатель {employer.username} одобрен.")
        elif action == 'reject_employer':
            employer.delete()
            messages.success(request, f"Заявка работодателя {employer.username} отклонена и удалена.")
        elif action == 'block_employer':
            employer.is_active = False
            employer.save()
            Notification.objects.create(
                user=employer,
                message=f"Ваш аккаунт в компании '{company.name}' заблокирован."
            )
            messages.success(request, f"Работодатель {employer.username} заблокирован.")
        return redirect('company_dashboard')

    return render(request, 'company_dashboard.html', {
        'user': request.user,
        'pending_employers': pending_employers,
        'approved_employers': approved_employers,
    })

@login_required
def employer_dashboard(request):
    if request.user.role == 'employer' and request.user.is_active and request.user.is_approved:
        tests = Test.objects.filter(created_by=request.user)

        search_query = request.GET.get('q', '')
        if search_query:
            tests = tests.filter(title__icontains=search_query)

        category_filter = request.GET.get('category_filter', '')
        if category_filter:
            tests = tests.filter(category_id=category_filter)

        position_filter = request.GET.get('position_filter', '')
        if position_filter:
            tests = tests.filter(position=position_filter)

        categories = Category.objects.all()
        if request.method == 'POST':
            title = request.POST['title']
            category_id = request.POST['category']
            position = request.POST.get('position', '')
            custom_position = request.POST.get('custom_position', '')
            if position == 'other' and custom_position:
                position = custom_position
            elif not position:
                position = None
            Test.objects.create(title=title, category_id=category_id, created_by=request.user, position=position)
            return redirect('employer_dashboard')

        assignments = TestAssignment.objects.filter(test__in=tests)
        assigned_count = assignments.count()
        completed_count = assignments.filter(is_active=False).count()
        avg_score = Answer.objects.filter(
            assignment__in=assignments,
            assignment__is_active=False
        ).aggregate(avg_score=Avg('manual_points'))['avg_score'] or 0

        stats = {
            'labels': ['Назначено', 'Завершено', 'Средний балл'],
            'data': [assigned_count, completed_count, round(avg_score, 2)],
            'backgroundColor': ['#007bff', '#28a745', '#ffc107']
        }

        applicants = CustomUser.objects.filter(role='applicant')
        if not applicants.exists():
            messages.warning(request, 'Нет соискателей с role="applicant" в базе данных.')
        elif request.user.company:
            applicants = applicants.filter(company=request.user.company)
            if not applicants.exists():
                messages.warning(request, 'Нет соискателей в компании работодателя.')
        else:
            messages.warning(request, 'У работодателя не указана компания. Показываю всех соискателей.')
            applicants = CustomUser.objects.filter(role='applicant')  # Показываем всех, если нет компании

        return render(request, 'employer_dashboard.html', {
            'tests': tests,
            'categories': categories,
            'stats': stats,
            'applicants': applicants,
        })
    elif request.user.role == 'employer' and not request.user.is_approved:
        messages.warning(request, 'Ваша заявка на роль работодателя еще не одобрена. Функции работодателя недоступны.')
        return render(request, 'pending_approval.html')
    messages.error(request, 'Ваш аккаунт заблокирован или доступ запрещён.')
    return redirect('login')

@login_required
def create_test(request):
    if request.user.role == 'employer' and request.user.is_active:
        if request.method == 'POST':
            title = request.POST['title']
            category_id = request.POST['category']
            time_limit = request.POST['time_limit']
            Test.objects.create(title=title, category_id=category_id, created_by=request.user, time_limit=time_limit)
            return redirect('employer_dashboard')
        categories = Category.objects.all()
        return render(request, 'create_test.html', {'categories': categories})
    messages.error(request, 'Ваш аккаунт заблокирован.')
    return redirect('login')

@login_required
def edit_test(request, test_id):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    if request.method == 'POST':
        test.title = request.POST['title']
        test.category_id = request.POST['category']
        test.save()
        return redirect('edit_test', test_id=test.id)
    categories = Category.objects.all()
    questions = Question.objects.filter(test=test)
    return render(request, 'edit_test.html', {'test': test, 'categories': categories, 'questions': questions})

@login_required
def edit_question(request, question_id):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')
    question = get_object_or_404(Question, id=question_id)
    if request.method == 'POST':
        question.text = request.POST['text']
        question.time_per_question = request.POST['time_per_question']
        question.category_id = request.POST['category']
        question.question_type = request.POST['question_type']
        question.save()
        return redirect('edit_test', test_id=question.test.id)
    categories = Category.objects.all()
    return render(request, 'edit_question.html', {'question': question, 'categories': categories})

@login_required
def delete_question(request, question_id):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')
    question = get_object_or_404(Question, id=question_id)
    test_id = question.test.id
    if request.method == 'POST':
        question.delete()
        return redirect('edit_test', test_id=test_id)
    return render(request, 'delete_question.html', {'question': question})

@login_required
def delete_test(request, test_id):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    if request.method == 'POST':
        test.delete()
        return redirect('employer_dashboard')
    return render(request, 'delete_test.html', {'test': test})

@login_required
@csrf_exempt
def create_question(request, test_id):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')
    test = get_object_or_404(Test, id=test_id, created_by=request.user)
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data['text']
        time_per_question = data['time_per_question']
        category_id = data['category']
        question_type = data['question_type']
        points = int(data.get('points', 1))
        question = Question.objects.create(
            test=test,
            text=text,
            time_per_question=time_per_question,
            category_id=category_id,
            question_type=question_type,
            points=points
        )
        if question_type in ['single', 'multiple']:
            for option_text, is_correct in data.get('options', []):
                Option.objects.create(question=question, text=option_text, is_correct=is_correct)
        return JsonResponse({'status': 'success'})
    categories = Category.objects.all()
    return render(request, 'create_question.html', {'test': test, 'categories': categories})

@login_required
def assign_test(request, test_id):
    if request.user.role == 'employer' and request.user.is_active and request.user.is_approved and request.user.company:
        test = get_object_or_404(Test, id=test_id, created_by=request.user)
        if request.method == 'POST':
            applicant_username = request.POST['applicant']
            applicant = get_object_or_404(CustomUser, username=applicant_username, role='applicant', company=request.user.company)
            TestAssignment.objects.create(test=test, applicant=applicant)
            messages.success(request, f'Тест "{test.title}" назначен соискателю {applicant.username}.')
            return redirect('employer_dashboard')
        applicants = CustomUser.objects.filter(role='applicant', company=request.user.company)
        if not applicants.exists():
            messages.warning(request, 'В вашей компании нет зарегистрированных соискателей.')
        return render(request, 'assign_test.html', {'test': test, 'applicants': applicants})
    messages.error(request, 'Ваш аккаунт заблокирован, не одобрен или не привязан к компании.')
    return redirect('login')

@login_required
def applicant_dashboard(request):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')

    if request.method == 'POST' and 'mark_read' in request.POST:
        notification_id = request.POST.get('notification_id')
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        messages.success(request, 'Уведомление отмечено как прочитанное.')
        return redirect('applicant_dashboard')

    notifications = request.user.notifications.all().order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()

    active_assignments = TestAssignment.objects.filter(applicant=request.user, is_active=True).select_related('test')

    completed_assignments = TestAssignment.objects.filter(applicant=request.user, is_active=False).select_related('test')

    profile = {
        'username': request.user.username,
        'email': request.user.email,
        'role': request.user.get_role_display(),
        'is_active': request.user.is_active,
        'company': request.user.company.name if request.user.company else 'Не указана',
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'position': request.user.position if request.user.position else 'Не указана'
    }

    accepted_count = completed_assignments.filter(is_accepted=True).count()
    rejected_count = completed_assignments.filter(is_rejected=True).count()
    pending_count = active_assignments.count()
    stats = {
        'labels': ['Приняты', 'Отклонены', 'В ожидании'],
        'data': [accepted_count, rejected_count, pending_count],
        'backgroundColor': ['#28a745', '#dc3545', '#6c757d']
    }

    return render(request, 'applicant_dashboard.html', {
        'profile': profile,
        'active_assignments': active_assignments,
        'completed_assignments': completed_assignments,
        'notifications': notifications,
        'unread_count': unread_count,
        'stats': stats,
    })

@login_required
@csrf_exempt
def take_test(request, assignment_id):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')
    assignment = get_object_or_404(TestAssignment, id=assignment_id, applicant=request.user)
    if request.method == 'POST':
        data = json.loads(request.body)
        question_id = data['question_id']
        answer_text = data.get('answer_text', '')
        selected_option_id = data.get('selected_option_id')
        selected_option_ids = data.get('selected_option_ids', [])
        time_taken = data.get('time_taken', 0)
        question = get_object_or_404(Question, id=question_id)
        answer, created = Answer.objects.get_or_create(assignment=assignment, question=question)
        if time_taken > 0:
            answer.answer_text = ','.join(map(str, selected_option_ids)) if selected_option_ids else answer_text
            answer.selected_option_id = selected_option_id
            answer.time_taken = time_taken
            answer.is_submitted = True
            answer.save()
            return JsonResponse({'status': 'success'})
    current_question = Question.objects.filter(test=assignment.test).exclude(
        id__in=Answer.objects.filter(assignment=assignment, is_submitted=True).values('question_id')).first()
    if not current_question:
        assignment.is_active = False
        assignment.save()
        return redirect('test_result', assignment_id=assignment.id)
    options = current_question.option_set.all()
    has_options = options.exists()
    is_multiple = current_question.question_type == 'multiple'
    return render(request, 'take_test.html', {
        'assignment': assignment,
        'current_question': current_question,
        'options': options,
        'has_options': has_options,
        'is_multiple': is_multiple,
    })

@login_required
def test_result(request, assignment_id):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')
    assignment = get_object_or_404(TestAssignment, id=assignment_id, applicant=request.user)
    answers = Answer.objects.filter(assignment=assignment)
    score = 0
    max_score = 0
    for answer in answers:
        question = answer.question
        options = question.option_set.all()
        if options.exists():
            max_score += question.points
            correct_options = set(str(opt.id) for opt in options if opt.is_correct)
            if answer.answer_text:
                selected_ids = set(answer.answer_text.split(','))
                if selected_ids == correct_options and correct_options:
                    score += question.points
            elif answer.selected_option and str(answer.selected_option.id) in correct_options:
                if len(correct_options) == 1:
                    score += question.points
    return render(request, 'test_result.html', {'score': score, 'max_score': max_score})

@login_required
def employer_reports(request):
    if not request.user.role == 'employer' or not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован или доступ запрещён.')
        return redirect('login')
    tests = Test.objects.filter(created_by=request.user)
    assignments = TestAssignment.objects.filter(test__in=tests).select_related('applicant', 'test')

    if request.method == 'POST':
        if 'assignment_id' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            is_accepted = request.POST.get('is_accepted')
            is_rejected = request.POST.get('is_rejected')
            assignment = get_object_or_404(TestAssignment, id=assignment_id, test__created_by=request.user)
            prev_status = {
                'accepted': assignment.is_accepted,
                'rejected': assignment.is_rejected
            }
            if is_accepted:
                assignment.is_accepted = True
                assignment.is_rejected = False
            elif is_rejected:
                assignment.is_accepted = False
                assignment.is_rejected = True
            assignment.save()

            if (is_accepted and not prev_status['accepted']) or (is_rejected and not prev_status['rejected']):
                message = (
                    f"Поздравляем! Вы приняты по результатам теста '{assignment.test.title}'."
                    if is_accepted else
                    f"К сожалению, вы отклонены по результатам теста '{assignment.test.title}'."
                )
                Notification.objects.update_or_create(
                    user=assignment.applicant,
                    test=assignment.test,
                    defaults={'message': message, 'is_read': False}
                )
        elif 'delete_assignment_id' in request.POST:
            delete_id = request.POST.get('delete_assignment_id')
            assignment = get_object_or_404(TestAssignment, id=delete_id, test__created_by=request.user)
            assignment.delete()
            return redirect('employer_reports')
        elif 'manual_score' in request.POST:
            answer_id = request.POST.get('answer_id')
            manual_points = int(request.POST.get('manual_score', 0))
            answer = get_object_or_404(Answer, id=answer_id, assignment__test__created_by=request.user)
            answer.manual_points = manual_points
            answer.save()
            return redirect('employer_reports')

    assignment_data = []
    for a in assignments:
        answers = []
        for ans in Answer.objects.filter(assignment=a).select_related('question', 'selected_option'):
            score = 0
            selected_text = []
            if ans.question.question_type == 'open':
                score = ans.manual_points
                selected_text = [ans.answer_text] if ans.answer_text else ["(нет ответа)"]
            elif ans.question.question_type == 'multiple' and ans.answer_text:
                selected_ids = ans.answer_text.split(',')
                selected_options = Option.objects.filter(id__in=selected_ids)
                selected_text = [opt.text for opt in selected_options]
                correct_ids = set(str(opt.id) for opt in ans.question.option_set.filter(is_correct=True))
                if set(selected_ids) == correct_ids and correct_ids:
                    score = ans.question.points
            elif ans.question.question_type == 'single' and ans.selected_option:
                selected_text = [ans.selected_option.text]
                if ans.selected_option.is_correct:
                    score = ans.question.points
            else:
                selected_text = ["(нет ответа)"]
            answers.append({
                'answer': ans,
                'score': score,
                'selected_text': selected_text
            })
        assignment_data.append({
            'assignment': a,
            'answers': answers,
        })

    status_counts = assignments.aggregate(
        accepted=Count('id', filter=Q(is_accepted=True)),
        rejected=Count('id', filter=Q(is_rejected=True)),
        pending=Count('id', filter=~Q(is_accepted=True) & ~Q(is_rejected=True))
    )
    chart_data = {
        'labels': ['Принято', 'Отклонено', 'Ожидает'],
        'data': [status_counts['accepted'], status_counts['rejected'], status_counts['pending']],
        'backgroundColor': ['#28a745', '#dc3545', '#6c757d']
    }

    return render(request, 'employer_reports.html', {
        'assignment_data': assignment_data,
        'chart_data': chart_data,
    })

def is_admin(user):
    return hasattr(user, 'role') and user.role == 'admin'

@login_required
def user_registration(request):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.company = form.cleaned_data['company']
            user.role = 'employer'
            user.is_approved = False
            user.save()
            messages.success(request, 'Ваша заявка отправлена администратору компании!')
            return redirect('login')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = UserRegistrationForm()
    return render(request, 'user_registration.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def manage_users(request):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')
    company = request.user.company
    pending_employers = CustomUser.objects.filter(company=company, role='employer', is_approved=False)
    approved_employers = CustomUser.objects.filter(company=company, role='employer', is_approved=True, is_active=True)
    blocked_employers = CustomUser.objects.filter(company=company, role='employer', is_approved=True, is_active=False)

    date_filter = request.GET.get('date_filter', '')
    if date_filter:
        from django.utils import timezone
        try:
            from_date = timezone.datetime.strptime(date_filter, '%Y-%m-%d').date()
            pending_employers = pending_employers.filter(date_joined__gte=from_date)
            approved_employers = approved_employers.filter(date_joined__gte=from_date)
            blocked_employers = blocked_employers.filter(date_joined__gte=from_date)
        except ValueError:
            pass

    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        if user_id and action:
            user = get_object_or_404(CustomUser, id=user_id, company=company, role='employer')
            if action == 'approve_employer':
                user.is_approved = True
                user.save()
                Notification.objects.create(
                    user=user,
                    message=f"Ваша заявка на роль работодателя в компании '{company.name}' одобрена."
                )
                messages.success(request, f"Работодатель {user.username} одобрен.")
            elif action == 'reject_employer':
                user.delete()
                messages.success(request, f"Заявка работодателя {user.username} отклонена и удалена.")
            elif action == 'block_employer':
                user.is_active = False
                user.save()
                Notification.objects.create(
                    user=user,
                    message=f"Ваш аккаунт в компании '{company.name}' заблокирован."
                )
                messages.success(request, f"Работодатель {user.username} заблокирован.")
            elif action == 'unblock_employer':
                user.is_active = True
                user.save()
                Notification.objects.create(
                    user=user,
                    message=f"Ваш аккаунт в компании '{company.name}' разблокирован."
                )
                messages.success(request, f"Работодатель {user.username} разблокирован.")
            elif action == 'delete_employer':
                user.delete()
                messages.success(request, f"Работодатель {user.username} удалён.")
        return redirect('manage_users')

    return render(request, 'manage_users.html', {
        'user': request.user,
        'pending_employers': pending_employers,
        'approved_employers': approved_employers,
        'blocked_employers': blocked_employers,
        'invitations': CompanyInvitation.objects.filter(company=company),
        'date_filter': date_filter,
    })

@staff_member_required
def company_approval_list(request):
    if not request.user.is_active:
        messages.error(request, 'Ваш аккаунт заблокирован.')
        return redirect('login')
    companies = Company.objects.filter(is_approved=False).order_by('created_at')
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        action = request.POST.get('action')
        company = get_object_or_404(Company, id=company_id)
        if action == 'approve':
            company.is_approved = True
            company.save()
            CustomUser.objects.filter(company=company, role='admin').update(is_approved=True)
            messages.success(request, f'Компания "{company.name}" одобрена.')
        elif action == 'reject':
            CustomUser.objects.filter(company=company, role='admin').delete()
            company.delete()
            messages.success(request, f'Компания "{company.name}" отклонена и удалена.')
        return redirect('company_approval_list')
    return render(request, 'company_approval_list.html', {'companies': companies})

@login_required
def invite_applicant(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            if not CompanyInvitation.objects.filter(email=email).exists():
                subject = 'Приглашение на регистрацию соискателя'
                message = f'Здравствуйте! Вы приглашены зарегистрироваться как соискатель. Перейдите по ссылке: http://127.0.0.1:8000/register/applicant/'
                from_email = settings.EMAIL_HOST_USER
                recipient_list = [email]
                try:
                    send_mail(subject, message, from_email, recipient_list)
                    CompanyInvitation.objects.create(email=email)
                    messages.success(request, f'Приглашение отправлено на {email}')
                except Exception as e:
                    messages.error(request, f'Ошибка отправки: {str(e)}')
            else:
                messages.error(request, 'Приглашение для этого email уже отправлено.')
        else:
            messages.error(request, 'Введите email адрес.')
        return redirect('manage_users')
    return render(request, 'invite_applicant.html')