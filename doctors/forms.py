from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import User, Specialty, Appointment, user_picture_path

import os

class BookForm(forms.Form):
    doctor_id = forms.IntegerField()
    # string of the form '<year><month><day>', e.g.: '20240125'
    date = forms.CharField(max_length=8)
    # string of the form '<hour>:<minutes>', e.g.: '10:30' 
    time = forms.CharField(max_length=5)

class CancelForm(forms.Form):
    appointment_id = forms.IntegerField()

class PictureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('picture',)

    def save(self):
        # Make sure no new filename (and file) is added to storage folder 
        #  when updating the picture
        # First save the user so we can rely on actual file name on disk
        user = super().save()
        if user.picture:
            # new name is the target name we want to have of the form 
            #   <username>.<ext>, e.g. alice.jpg
            new_name = user_picture_path(user, user.picture.name)
            if user.picture.name != new_name:
                initial_path = user.picture.path
                user.picture.name = new_name
                new_path = os.path.join(settings.MEDIA_ROOT, user.picture.name)
                os.remove(new_path)
                os.rename(initial_path, new_path)
                user.save()
        return user

USER_TEXT_FIELDS = (
    'username', 'password', 'password_confirm', 'first_name', 
    'last_name', 'email', 'description', 
)
class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = USER_TEXT_FIELDS + ('is_doctor', 'specialty')
        widgets = {
            'description': forms.Textarea(attrs={'rows': '2'}),
        }

    # add bootstrap classes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in USER_TEXT_FIELDS:
            self.fields[field].widget.attrs.update(
                {'class': 'form-control'})
        self.fields['is_doctor'].widget.attrs.update(
            {'class': 'form-check-input'})  
        self.fields['specialty'].widget.attrs.update(
            {'class': 'form-select'})

    def clean_password_confirm(self):
        # Check that the two passwords match
        password = self.cleaned_data.get("password")
        password_confirm = self.cleaned_data.get("password_confirm")
        if (password and 
            password_confirm and 
            password != password_confirm):
            # here validation has failed
            raise ValidationError("Passwords do not match.")
        # here passwords match
        return password

    def clean_specialty(self):
        # doctors must choose a specialty
        is_doctor = self.cleaned_data.get("is_doctor")
        specialty = self.cleaned_data.get("specialty")
        if is_doctor and specialty is None:
            raise ValidationError("Choose a medical specialty.")
        return specialty

    def save(self):
        # Create user instance
        user = super().save(commit=False)
        # Save password in hashed format
        user.set_password(self.cleaned_data.get("password"))
        # Insert user into database
        user.save()
        return user

# had to create a regular form (not a model form) because I was getting
# the error that the username and the email already exist
class UserUpdateForm(forms.Form):
    # this form does not handle changing the password
 
    username = forms.CharField(max_length=150)
    username.widget.attrs.update({'class': 'form-control'})

    first_name = forms.CharField(max_length=128)
    first_name.widget.attrs.update({'class': 'form-control'})

    last_name = forms.CharField(max_length=128)
    last_name.widget.attrs.update({'class': 'form-control'})

    email = forms.EmailField(max_length=150)
    email.widget.attrs.update({'class': 'form-control'})

    is_doctor = forms.BooleanField(required=False)
    is_doctor.widget.attrs.update({'class': 'form-check-input'})

    # specialty choices (select options) are set in the __init__ method below
    specialty = forms.ChoiceField(required=False)
    specialty.widget.attrs.update({'class': 'form-select'})

    description = forms.CharField(required=False, widget=forms.Textarea(
        attrs={'rows': '2', 'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        # add select options to specialties form field
        specialties = Specialty.objects.values()
        select_options = [("", "---------")]
        for specialty in specialties:
            select_options.append((specialty['id'], specialty['name']))
        self.fields['specialty'].choices = select_options

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.exclude(pk=self.user.id).filter(username=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.exclude(pk=self.user.id).filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_specialty(self):
        # doctors must choose a specialty
        is_doctor = self.cleaned_data.get("is_doctor")
        specialty = self.cleaned_data.get("specialty")
        if is_doctor and not specialty:
            raise ValidationError("Choose a medical specialty.")
        return specialty


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}), 
        max_length=150)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        max_length=150)