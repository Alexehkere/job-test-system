from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # Подключение всех маршрутов аутентификации
    path('', include('tests_app.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]