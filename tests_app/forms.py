from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Company, CompanyInvitation
import re

class CompanyRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, label='Имя пользователя', help_text='Введите уникальное имя пользователя для администратора компании.')
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput, help_text='Пароль должен содержать минимум 8 символов.')
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput, help_text='Повторите пароль.')
    phone_number = forms.CharField(max_length=20, label='Номер телефона', required=False, help_text='Формат: +1234567890 или 123-456-7890')

    class Meta:
        model = Company
        fields = ['name', 'contact_email', 'phone_number', 'description']

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('Это имя пользователя уже занято.')
        return username

    def clean_contact_email(self):
        email = self.cleaned_data['contact_email']
        if not email.endswith('@gmail.com'):
            raise forms.ValidationError('Пожалуйста, используйте email на gmail.com')
        if Company.objects.filter(contact_email=email).exists():
            raise forms.ValidationError('Этот email уже зарегистрирован.')
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if phone_number and not re.match(r'^\+?[\d\s-]{10,15}$', phone_number):
            raise forms.ValidationError('Номер телефона должен содержать от 10 до 15 цифр и может включать +, пробелы или дефисы.')
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Пароли не совпадают.')
        if password1 and len(password1) < 8:
            raise forms.ValidationError('Пароль должен содержать минимум 8 символов.')
        return cleaned_data

class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, label='Имя', required=False)
    last_name = forms.CharField(max_length=30, label='Фамилия', required=False)
    position = forms.CharField(max_length=100, label='Должность', required=False, help_text='Необязательно, пример: Дизайнер, Программист')
    company = forms.ModelChoiceField(queryset=Company.objects.filter(is_approved=True), label='Компания', required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'position', 'company']
        labels = {
            'username': 'Логин',
            'email': 'Email',
            'password1': 'Пароль',
            'password2': 'Подтв. пароля',
        }
        help_texts = {
            'username': 'Требуется. До 150 символов. Допустимы буквы, цифры и @/./+/-/_',
            'password2': 'Введите тот же пароль для проверки.',
        }

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        if 'initial' in kwargs and 'role' in kwargs['initial']:
            self.initial['role'] = kwargs['initial']['role']
        if 'initial' in kwargs and kwargs['initial'].get('role') != 'applicant':
            self.fields['first_name'].widget = forms.HiddenInput()
            self.fields['last_name'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        role = self.initial.get('role', 'applicant')
        if role == 'applicant' and not (cleaned_data.get('first_name') and cleaned_data.get('last_name')):
            raise forms.ValidationError("Для соискателя имя и фамилия обязательны.")
        return cleaned_data

class CompanyInvitationForm(forms.ModelForm):
    class Meta:
        model = CompanyInvitation
        fields = ['user']

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['user'].queryset = CustomUser.objects.filter(
                role='applicant',
                company=company,
                is_approved=True
            )