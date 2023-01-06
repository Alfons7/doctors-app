from django.utils.html import escape
from django.core.mail import send_mail
from django.conf import settings
import datetime

# used in the search view
def doctor_to_dict(doctor):
    '''
    Convert a doctor object returned by the query to the dictionary
    expected by the front end
    '''
    return {
        'doctor_id': doctor['id'],
        # escape user generated content to prevent XSS attacks
        'doctor_name': escape(f"{doctor['first_name']} {doctor['last_name']}"),
        'doctor_specialty': doctor['specialty__name'],
        'doctor_img': escape(doctor['picture']),
    }

def next_weekday(date):
    next_day = date + datetime.timedelta(days=1)
    while next_day.weekday() >= 5:  # 5 means Saturday, 6 Sunday
        next_day += datetime.timedelta(days=1)
    return next_day

# used in the book view
def next_weekdays(date, num_days):
    '''
    Returns the next num_days weekdays (skipping weekend days) 
    starting with the day after the given date
    '''
    next_days = []
    next_day = next_weekday(date)
    while len(next_days) < num_days:
        next_days.append(next_day)
        next_day = next_weekday(next_day)
    return next_days

def confirmation_email(to_first_name, to_email, doctor, date, time):
    '''
    Send email to confirm an appointment
    to_first_name and to_mail refer to the recipient of the message (the patient)
    doctor is the doctor the recipient will have the appointment with
    '''
    subject = 'Appointment confirmation'
    message = (f"Dear {to_first_name},\n"
               f"We are glad to confirm your appointment with Doctor {doctor} on {date} at {time}.\n"
                "Best regards,\n"
                "The Doctors Team")
    send_mail(
        subject=subject,
        message=message,
        from_email=f'''"Doctors App" <{settings.EMAIL_HOST_USER}@gmail.com>''',
        recipient_list=[to_email]
    )

def cancellation_email(to_first_name, to_email, doctor, date, time):
    '''
    Send email to confirm a cancellation
    to_first_name and to_mail refer to the recipient of the message (the patient)
    doctor is the doctor the recipient had the appointment with
    '''
    subject = 'Appointment cancellation'
    message = (f"Dear {to_first_name},\n"
               f"Your appointment with Doctor {doctor} on {date} at {time} has been cancelled.\n"
                "Best regards,\n"
                "The Doctors Team")
    send_mail(
        subject=subject,
        message=message,
        from_email=f'''"Doctors App" <{settings.EMAIL_HOST_USER}@gmail.com>''',
        recipient_list=[to_email]
    )