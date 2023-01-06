from django.contrib import admin

# Register your models here.

from .models import User, Specialty, Appointment


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'is_doctor', 'specialty')

admin.site.register(User, UserAdmin)


class SpecialtyAdmin(admin.ModelAdmin):
    pass

admin.site.register(Specialty, SpecialtyAdmin)


class AppointmentAdmin(admin.ModelAdmin):
    pass

admin.site.register(Appointment, AppointmentAdmin)