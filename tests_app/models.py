from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
import re
from django.core.exceptions import ValidationError

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Test(models.Model):
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    position = models.CharField(max_length=100, blank=True, null=True, help_text="Должность для теста (можно выбрать или ввести вручную)")  # Новое поле для должности
    def __str__(self):
        return self.title

class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    text = models.TextField()
    time_per_question = models.IntegerField(default=60)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    question_type = models.CharField(max_length=50, choices=[('single', 'Один вариант'), ('multiple', 'Несколько вариантов'), ('open', 'Развернутый ответ')], default='single')
    points = models.PositiveIntegerField(default=1, help_text="Сколько баллов за этот вопрос")
    def __str__(self):
        return self.text[:50]

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    def __str__(self):
        return self.text

class TestAssignment(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_tests')
    is_active = models.BooleanField(default=True)
    is_accepted = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.applicant.username} - {self.test.title}"

class Answer(models.Model):
    assignment = models.ForeignKey(TestAssignment, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True, null=True)
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE, null=True, blank=True)
    time_taken = models.IntegerField(default=0)
    is_submitted = models.BooleanField(default=False)
    manual_points = models.PositiveIntegerField(default=0, help_text="Ручные баллы для открытых вопросов")
    def __str__(self):
        return f"{self.question.text[:20]} - {self.answer_text[:20]}"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True)
    def __str__(self):
        return f"Уведомление для {self.user.username} - {'прочитано' if self.is_read else 'непрочитано'}"

class Company(models.Model):
    name = models.CharField(max_length=150, unique=True)
    contact_email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.phone_number:
            if not re.match(r'^\+?[\d\s-]{10,15}$', self.phone_number):
                raise ValidationError('Номер телефона должен содержать от 10 до 15 цифр и может включать +, пробелы или дефисы.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('employer', 'Работодатель'),
        ('applicant', 'Соискатель'),
        ('admin', 'Администратор компании'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    position = models.CharField(max_length=100, blank=True, null=True, default=None, help_text="Должность соискателя")

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class CompanyInvitation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('company', 'user')

class Invitation(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email