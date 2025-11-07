from django.contrib import admin
from .models import Company, CustomUser, Category, Test, Question, Option, TestAssignment, Answer, Notification, CompanyInvitation

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_email', 'phone_number', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('name', 'contact_email')
    actions = ['approve_companies', 'reject_companies']

    def approve_companies(self, request, queryset):
        queryset.update(is_approved=True)
        for company in queryset:
            # Одобряем всех пользователей с ролью admin, связанных с компанией
            CustomUser.objects.filter(company=company, role='admin').update(is_approved=True)
        self.message_user(request, f"Выбранные компании успешно одобрены.")
    approve_companies.short_description = "Одобрить выбранные компании"

    def reject_companies(self, request, queryset):
        count = queryset.count()
        for company in queryset:
            # Удаляем связанных пользователей с ролью admin
            CustomUser.objects.filter(company=company, role='admin').delete()
            company.delete()
        self.message_user(request, f"{count} компаний успешно отклонены и удалены.")
    reject_companies.short_description = "Отклонить и удалить выбранные компании"

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'company', 'is_approved')
    list_filter = ('role', 'is_approved')
    search_fields = ('username', 'email')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'created_by', 'position')
    list_filter = ('category',)
    search_fields = ('title',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'test', 'category', 'question_type', 'points')
    list_filter = ('question_type', 'category')
    search_fields = ('text',)

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ('text', 'question', 'is_correct')
    list_filter = ('is_correct',)

@admin.register(TestAssignment)
class TestAssignmentAdmin(admin.ModelAdmin):
    list_display = ('test', 'applicant', 'is_active', 'is_accepted')
    list_filter = ('is_active', 'is_accepted')

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'assignment', 'answer_text', 'is_submitted')
    list_filter = ('is_submitted',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')

@admin.register(CompanyInvitation)
class CompanyInvitationAdmin(admin.ModelAdmin):
    list_display = ('company', 'user', 'is_accepted', 'created_at')
    list_filter = ('is_accepted', 'created_at')