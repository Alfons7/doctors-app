from django.urls import path

from . import views

app_name = 'doctors'
urlpatterns = [
    # Search for doctors
    path("", views.index, name="index"),
    path("search/", views.search, name="search"), # API endpoint. Returns JSON.

    # Book and manage appointments
    path("book/<int:doctor_id>", views.book, name="book"),
    path("book/slots", views.time_availabilities, name="time-slots"), # API endpoint.
    path("book/confirm", views.appointment_book, name="book-confirm"), # API endpoint.
    path("appointments", views.appointments, name="appointments"),
    path("appointments/cancel", views.appointment_cancel, name="appointments-cancel"), # API endpoint.

    # User personal data and picture uploading
    path("users/<int:user_id>", views.user_detail, name="user-detail"),
    path("users/<int:user_id>/update", views.user_update, name="user-update"),
    path("users/upload", views.upload, name="upload"), # API endpoint.

    # Registration, login, logout
    path("register", views.register, name="register"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
]