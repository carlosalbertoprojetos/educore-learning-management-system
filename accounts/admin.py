from django.contrib import admin


from .models import User
# Register your models here.


class UserAdmin(admin.ModelAdmin):
    model = User
    list_display = ['username', 'email', 'is_active']

admin.site.register(User, UserAdmin)
