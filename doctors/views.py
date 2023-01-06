from django.contrib import messages
from django.urls import reverse
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.conf import settings

import datetime as dt

from .models import User, Specialty, Appointment

from .forms import BookForm, CancelForm, UserCreateForm, UserUpdateForm, PictureForm, LoginForm

from .helpers import confirmation_email, cancellation_email, doctor_to_dict, next_weekdays

#
# Find a doctor
#
def index(request):
    return render(request, 'doctors/index.html')

# API endpoint. Returns JSON.
def search(request):
    search_term = request.GET.get("search_term")
    if search_term is None:
        return HttpResponse(status=400) # bad request
    # build query object to search doctors across first_name, last_name 
    #   and specialty
    query = Q(is_doctor=True)
    query_matches_term = Q(first_name__icontains=search_term)
    query_matches_term.add(Q(last_name__icontains=search_term), Q.OR)
    query_matches_term.add(Q(specialty__name__icontains=search_term), Q.OR)
    query.add(query_matches_term, Q.AND)
    doctors_query_set = User.objects.filter(query).values(
        'id', 'first_name', 'last_name', 'specialty__name', 'picture')
    doctors_list = list(map(doctor_to_dict, doctors_query_set))
    return JsonResponse({'results': doctors_list}, status=200)


#
# Book and manage appointments
#
@login_required
def book(request, doctor_id):
    # Number of dates to display on the booking screen
    NUM_DATES = 10
    doctor = get_object_or_404(User, pk=doctor_id)
    if not doctor.is_doctor:
        return HttpResponse(status=400) # bad request
    # Make sure doctors cannot book appointments with themselves
    if request.user == doctor:
        return HttpResponseRedirect(reverse("doctors:index"))
    dates = next_weekdays(dt.date.today(), NUM_DATES)
    return render(request, 'doctors/book.html', {
        'doctor': doctor,
        'dates': dates,
    })

# API endpoint
@login_required
def time_availabilities(request):
    doctor_id = request.GET.get("doctor_id")
    date = request.GET.get("date")
    if doctor_id is None or date is None:
        return HttpResponse(status=400) # bad request
    doctor = get_object_or_404(User, pk=doctor_id)
    if not doctor.is_doctor:
        return HttpResponse(status=400) # bad request
    try:
        date_object = dt.datetime.strptime(date, "%Y%m%d").date()
    except:
        return HttpResponse(status=400) # bad request
    time_slots = doctor.available_time_slots(date_object)
    time_slot_strings = [time_slot.strftime("%H:%M") for time_slot in time_slots];
    return JsonResponse({'time_slots': time_slot_strings}, status=200)


# API endpoint.
@login_required
def appointment_book(request):
    def flash_problem():
        messages.add_message(
            request, messages.INFO, 'We were not able to book your appointment.', 'danger')
    if request.method != 'POST':
        flash_problem()
        return HttpResponse(status=400) # bad request
    form = BookForm(request.POST)
    if form.is_valid():
        doctor_id = form.cleaned_data.get('doctor_id')
        date_string = form.cleaned_data.get('date')
        time_string = form.cleaned_data.get('time')
        doctor = get_object_or_404(User, pk=doctor_id)
        if not doctor.is_doctor:
            flash_problem()
            return HttpResponse(status=400) # bad request
        patient = request.user;
        try:
            date = dt.datetime.strptime(date_string, "%Y%m%d").date()
            time = dt.datetime.strptime(time_string, "%H:%M").time() 
            
        except:
            flash_problem()
            return HttpResponse(status=400) # bad request
        else:
            if patient.slot_is_taken(date, time):
                messages.add_message(
                    request, messages.INFO, 'You already have another appointment at the time you chose.', 'danger')
                return HttpResponse(status=400) # bad request
            doctor.book(patient, date, time)
            # make sure the email configuration has been set
            if settings.EMAIL_HOST_USER:
                # Send email to the patient.
                try:
                    confirmation_email(
                        to_first_name=patient.first_name, 
                        to_email=patient.email, 
                        doctor=doctor.get_full_name(),
                        date=date.strftime("%d %B %Y"), 
                        time=time.strftime("%H:%M"),)
                except Exception as e: 
                    print(e)
            messages.add_message(
                request, messages.INFO, f"Your appointment with Doctor {doctor.get_full_name()} has been booked.", 'info')
            return HttpResponse(status=204) # no content
    else:
        flash_problem()
        return HttpResponse(status=400) # bad request


@login_required
def appointments(request):
    if request.user.is_doctor:
        # doctors may book appointments (as patients) with other doctors
        query = Q(doctor=request.user)
        query.add(Q(patient=request.user), Q.OR)
        appointments = Appointment.objects.filter(query).select_related('patient').all()
    else:
        appointments = Appointment.objects.filter(patient=request.user).select_related('doctor').all()
    return render(request, 'doctors/appointments.html', {
        'appointments': appointments,
    })


# API endpoint.
@login_required
def appointment_cancel(request):
    def flash_problem():
        messages.add_message(
            request, messages.INFO, 'We were not able to cancel your appointment.', 'danger')
    if request.method != 'POST':
        flash_problem()
        return HttpResponse(status=400) # bad request
    form = CancelForm(request.POST)
    if form.is_valid():
        appointment_id = form.cleaned_data.get('appointment_id')
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        if appointment.doctor != request.user and appointment.patient != request.user:
            flash_problem()
            return HttpResponse(status=400) # bad request
        appointment.delete()
        messages.add_message(
            request, messages.INFO, 'Your appointment has been cancelled.', 'info')
        # make sure the email configuration has been set
        if settings.EMAIL_HOST_USER:
            # Send email to the patient.
            try:
                cancellation_email(
                    to_first_name=appointment.patient.first_name, 
                    to_email=appointment.patient.email, 
                    doctor=appointment.doctor.get_full_name(), 
                    date=appointment.date.strftime("%d %B %Y"), 
                    time=appointment.time.strftime("%H:%M"),)
            except Exception as e: 
                    print(e)
        return HttpResponse(status=204) # no content
    else:
        flash_problem()
        return HttpResponse(status=400) # bad request


#
# View and update user details, and upload a picture
#
@login_required
def user_detail(request, user_id):
    if request.method == 'GET':
        user = get_object_or_404(User, id=user_id)
        return render(request, 'doctors/user_detail.html', {
            'form': PictureForm()
        })
    else:
        return HttpResponse(status=400) # bad request


@login_required
def user_update(request, user_id):
    # note that the password is not updated through this view
    ACTION = 'UPDATE'

    # make sure the user exists
    user = get_object_or_404(User, pk=user_id)
    # make sure current users are updating their own user data
    if user.id != request.user.id:
        return HttpResponse(status=400) # bad request
    
    if request.method == 'GET':
        user_as_dict = {
            'username': request.user.username,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
        if user.is_doctor:
            user_as_dict['is_doctor'] = True
            user_as_dict['specialty'] = request.user.specialty.id
            user_as_dict['description'] = request.user.description
        form = UserUpdateForm(initial=user_as_dict, user=None)
        return render(request, 'doctors/user_form.html', {
            'form': form,
            'action': ACTION,
        })
    elif request.method == 'POST':
        form = UserUpdateForm(request.POST, user=request.user)
        if form.is_valid():
            user.username = form.cleaned_data.get('username')
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.email = form.cleaned_data.get('email')
            if form.cleaned_data.get('is_doctor'):
                specialtyInstance = get_object_or_404(
                    Specialty, id=form.cleaned_data.get('specialty'))
                user.is_doctor = True
                user.specialty = specialtyInstance
                user.description = form.cleaned_data.get('description')
            else:
                user.is_doctor = False
            user.save()
            # the extra_tag, 'info', is used to specify the type of bootstrap alert
            messages.add_message(
                request, messages.INFO, 'You have updated your data.', extra_tags='info')
            return HttpResponseRedirect(reverse("doctors:user-detail", args=(user.id,)))
        else:
            return render(request, 'doctors/user_form.html', {
                'form': form,
                'action': ACTION,
            })
    else:
        return HttpResponse(status=400) # bad request


# API endpoint.
@login_required
def upload(request):
    if request.method == 'POST':
        user = get_object_or_404(User, id=request.user.id)
        form = PictureForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            # note that when a user instance already has a picture, the form
            # validates even if the user not chosen a file to upload
            form.save()
            return HttpResponse(status=204) # no content
        else:
            # send errors as json to front end
            errors = dict(form.errors.items())
            return JsonResponse({'errors': errors}, status=422) # unprocessable entity
    else:
        return HttpResponse(status=400) # bad request


#
# register, login, logout
#
def register(request):
    ACTION = 'REGISTER'
    if request.method == 'GET':
        form = UserCreateForm()
        return render(request, 'doctors/user_form.html', {
            'form': form,
            'action': ACTION,
        })
    elif request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            # the extra_tag, 'info', is used to specify the type of bootstrap alert
            messages.add_message(
                request, messages.INFO, 'You have registered. Please log in.', extra_tags='info')
            return HttpResponseRedirect(reverse("doctors:login"))
        else:
            return render(request, 'doctors/user_form.html', {
                'form': form,
                'action': ACTION,
            })  
    else:
        return HttpResponse(status=400) # bad request


def login_view(request):
    if request.method == 'GET':
        form = LoginForm()
        return render(request, 'doctors/login.html', {
            'form': form,
            'next': request.GET.get("next", ""),
        })
    elif request.method == 'POST':
        form = LoginForm(request.POST)
        next = request.POST.get("next", "")
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # attach authenticated user to current session
                login(request, user)
                messages.add_message(
                    request, messages.INFO, 'You have logged in.', 'info')
                if next:
                    return HttpResponseRedirect(next)
                elif not user.is_doctor:
                    return HttpResponseRedirect(reverse("doctors:index"))
                # user is a doctor
                else:
                    return HttpResponseRedirect(reverse("doctors:appointments"))
            else:
                form.add_error(None, 'Wrong username and/or password.')
        return render(request, 'doctors/login.html', {
            'form': form,
            'next': next,
        })
    else:
        return HttpResponse(status=400) # bad request


def logout_view(request):
    # remove all session data
    logout(request)
    messages.add_message(
        request, messages.INFO, 'You have logged out.', 'info')
    return HttpResponseRedirect(reverse("doctors:login"))