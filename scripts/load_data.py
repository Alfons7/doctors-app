# Load initial data into the database:
#   specialties, doctors, patients, and initial appointments
# Note you will need to recreate the superuser after running this script
# Free doctor and patient images from pexels.com in images/ folder
#
# Usage:
#   python manage.py runscript load_data

from doctors.models import Specialty, User, Appointment
from doctors.helpers import next_weekday
import datetime

EASY_PASSWORD = 'w'

specialties = [
    'Allergology', 'Anaesthesiology', 'Cardiology', 
    'Dentist', 'Dermatology', 'Endocrinology', 
    'General Practitioner', 'Nephrology', 'Neurology', 
    'Ophthalmologist', 'Pediatrics', 'Psychiatry',
]

doctors = [
    # (username, first_name, last_name, email, specialty, description, picture)
    ('fred', 'fred', 'smith', 'fred@doctors.fr', 'Dentist', '', 'fred.jpg'),
    ('james', 'jaime', 'alvarez', 'james@doctors.fr', 'Dentist', '', 'james.jpg'),
    ('peter', 'peter', 'anderson', 'peter@doctors.fr', 'Dentist', '', 'peter.jpg'),
    ('maria', 'maria', 'strong', 'maria@doctors.fr', 'Dermatology', 
        '20+ years of experience in the American Hospital of Paris.', 'maria.jpg'),
    ('ines', 'ines', 'davis', 'ines@doctors.fr', 'Dermatology', '', 'ines.jpg'),
    ('isabel', 'isabel', 'vinci', 'isa@hospital.org', 'Dermatology', '', 'isabel.jpg'),
    ('jane', 'jane', 'jones', 'jane@hospital.org', 'General Practitioner', '', 'jane.jpg'),
    ('olivia', 'olivia', 'anderson', 'olivia@hospital.org', 'General Practitioner', '', 'olivia.jpg'),
    ('lucy', 'lucy', 'twice', 'lucy@hospital.org', 'Psychiatry', '', 'lucy.jpg'),
    ('denise', 'denise', 'diaz', 'denis@independent-doctors.org', 'Cardiology', '', 'denise.jpg'),
]

patients = [
    # (username, first_name, last_name, email, picture)
    ('alice', 'alice', 'adams', 'alice@foo.us', 'alice.jpg'),
    ('susan', 'susan', 'harris', 'susan@it.com', 'susan.jpg'),
    ('dan', 'dan', 'coco', 'dan@canal-plus.fr', 'dan.jpg'),
    ('matias', 'matias', 'sanjuan', 'matias@creative.cat', 'matias.jpg'),
    ('alfons', 'alfons', 'trabal', 'alfonstrabal@yahoo.fr', 'alfons.jpg'),
]

today = datetime.date.today()
next_day = next_weekday(today)
day_after = next_weekday(next_day)
appointments = [
    # (patient_username, doctor_username, date, time)
    ('alice', 'maria', next_day, datetime.time(11, 00)),
    ('susan', 'maria', next_day, datetime.time(11, 30)),
    ('dan', 'maria', next_day, datetime.time(15, 00)),
    ('matias', 'maria', next_day, datetime.time(15, 30)),
    ('alice', 'maria', day_after, datetime.time(10, 00)),
    ('alfons', 'olivia', day_after, datetime.time(16, 00)),
    ('alfons', 'ines', next_weekday(day_after), datetime.time(14, 00)),
    ('alfons', 'james', next_weekday(day_after), datetime.time(17, 00)),
]

def run():
    # clear specialties and users
    Specialty.objects.all().delete()
    User.objects.all().delete()
    Appointment.objects.all().delete()

    # add specialties (after clearing any previous ones)
    for specialty in specialties:
        Specialty.objects.create(name=specialty)

    # add doctors    
    for username, first_name, last_name, email, specialty, description, picture in doctors:
        specialty = Specialty.objects.get(name=specialty)
        User.objects.create_user(
            username=username, email=email, password=EASY_PASSWORD,
            first_name=first_name, last_name=last_name, is_doctor=True,
            specialty=specialty, description=description, picture=picture)
        
    # add patients
    for username, first_name, last_name, email, picture in patients:
        User.objects.create_user(
            first_name=first_name, last_name=last_name, username=username, 
            email=email, password=EASY_PASSWORD, picture=picture)

    # book appointments
    for patient_username, doctor_username, date, time in appointments:
        patient = User.objects.get(username=patient_username)
        doctor = User.objects.get(username=doctor_username)
        doctor.book(patient, date, time)

    print(f"Done loading initial data into the database:")
    print(f"  Added {len(specialties)} specialties, {len(doctors)} doctors, {len(patients)} patients, and {len(appointments)} appointments")
    print(f"You need to create a superuser account. Execute:")
    print(f"  python manage.py createsuperuser")