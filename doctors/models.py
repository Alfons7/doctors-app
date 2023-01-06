from django.db import models
from django.db.utils import IntegrityError
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError

import pathlib # to extract the extension of user uploaded files
import datetime

from .helpers import next_weekday

MAX_SIZE = 1024 * 1024 # maximum size of pictures uploaded by users

# helper function to validate the size of uploaded pictures
def validate_size(picture):
    if picture.file.size > MAX_SIZE:
        raise ValidationError("Choose a smaller file.")

# helper function to set the filename of pictures 
def user_picture_path(instance, filename):
# return filenames of the form username.extension, e.g.: alice.jpg
    extension = pathlib.Path(filename).suffix
    return f'{instance.username}{extension}'


class Specialty(models.Model):
    '''
    Medical specialty of doctors
    '''
    name = models.CharField(max_length=64, unique=True)

    def save(self, *args, **kwargs):
        # capitalize the first letter of specialties
        self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Appointment(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_appointments")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_appointments")
    date = models.DateField(db_index=True)

    TIME_SLOTS_SET = set(
        datetime.time(hour, minutes) for hour, minutes in [
            (10, 00), (10, 30), (11, 00), (11, 30), (12, 00), (14, 00), 
            (14, 30), (15, 00), (15, 30), (16, 00), (16, 30), (17, 00)])
    
    TIME_CHOICES = [(time, str(time)[:-3]) for time in TIME_SLOTS_SET]
    
    time = models.TimeField(choices=TIME_CHOICES)

    class Meta:
        unique_together = ('patient', 'doctor', 'date', 'time')
        ordering = ('date', 'time')

    def save(self, *args, **kwargs):
        # make sure date is a future week day
        if self.date < next_weekday(datetime.date.today()):
            raise ValueError(f"{self.date} is not a future week day.")
        # check doctors are doctors
        if not self.doctor.is_doctor:
            raise ValueError(f"{self.doctor.username} is not a doctor.")
        # a doctor cannot book an appointment with himself/herself
        elif self.patient == self.doctor:
            raise ValueError(f"{self.patient.username} cannot book an appointment with himself/herself.")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Patient {self.patient.username}, Doctor {self.doctor.username}: {self.date}{self.time}"


class User(AbstractUser):
    '''
    Both doctors and patients are users but for doctors the built-in user field 
    is_doctor is true
    '''
    is_doctor = models.BooleanField(default=False, db_index=True)
    
    # Only doctors have a specialty, for patients this field is null
    specialty = models.ForeignKey('Specialty', on_delete=models.SET_NULL, null=True, blank=True)
    # Doctors can provide a brief description
    description = models.CharField(max_length=512, blank=True, default='')

    # Picture of the patient or doctor
    picture = models.ImageField(
        upload_to=user_picture_path, null=True, blank=True, validators=[validate_size])

    # Both patients and doctors must provide their names
    first_name = models.CharField(
        max_length=128, validators=[MinLengthValidator(1, 'This field is required.')], db_index=True)
    last_name = models.CharField(
        max_length=128, validators=[MinLengthValidator(1, 'This field is required.')], db_index=True)

    # Emails must be unique
    email = models.EmailField(unique=True, max_length=150)

    # Two additional fields from the related_name of the Appointment model
    #   patient_appointments
    #   doctor_appointments

    def book(self, patient, date, time):
        try:
            Appointment.objects.create(patient=patient, doctor=self, date=date, time=time)
        except IntegrityError:
            pass

    def unbook(self, patient, date, time):
        appointment = Appointment.objects.filter(patient=patient, doctor=self, date=date, time=time).first()
        if appointment:
            appointment.delete()

    def available_time_slots(self, date):
        '''
        Returns list of Python time object for each available slot 
        the doctor has on the given date, sorted in ascending order
        '''
        # only doctors can suggest dates
        if not self.is_doctor:
            raise ValueError(f"{self.doctor.username} is not a doctor")
        # include appointments where the doctor has acted as patient and booked another doctor
        query = models.Q(date=date)
        query_patient_doctor = models.Q(doctor=self)
        query_patient_doctor.add(models.Q(patient=self), models.Q.OR)
        query.add(query_patient_doctor, models.Q.AND)

        appointments = Appointment.objects.filter(query).values()
        appointments_times_set = set(appointment['time'] for appointment in appointments)
        return sorted(Appointment.TIME_SLOTS_SET - appointments_times_set)

    def upcoming_appointments(self):
        if self.is_doctor:
            appointments = self.doctor_appointments
        else: 
            appointments = self.patient_appointments
        next_day = next_weekday(datetime.date.today())
        return appointments.filter(date__gte=next_day).values()

    def slot_is_taken(self, date, time):
        '''
        Used to avoid that a patient takes two 
        appointments at the same time
        '''
        return Appointment.objects.filter(patient=self, date=date, time=time)

    def __str__(self):
        title = 'Doctor' if self.is_doctor else 'Patient'
        return f"{title}: {self.username}"

    def save(self, *args, **kwargs):
        # Capitalize first letter of first and last names
        self.first_name = self.first_name.title()
        self.last_name = self.last_name.title()
        # If user is not a doctor, no pecialty or description should be saved
        if not self.is_doctor:
            self.specialty = None
            self.description = ''
        super().save(*args, **kwargs)