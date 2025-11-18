from django.contrib import admin
from .models import CustomUser
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Qualification


#Custom User------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active']
    ordering = ['-created_at']
    search_fields = ['email', 'first_name', 'last_name']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'qualification', 'activated_at', 'deactivated_at')}),
    )

admin.site.register(Qualification)