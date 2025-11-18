from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Qualification, AssessmentCentre, CustomUser, QuestionBankEntry, Assessment
from django.contrib.auth import get_user_model


User = get_user_model()

class CustomUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'qualification', 'is_active', 'student_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'qualification': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(),
            'student_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AssessmentCentreForm(forms.ModelForm):
    class Meta:
        model = AssessmentCentre
        fields = ['name', 'location', 'qualification_assigned']



User = get_user_model()

class EmailRegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Email address", required=True)
    first_name = forms.CharField(label="First name", required=True)
    last_name = forms.CharField(label="Last name", required=True)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        user.username = user.email
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.role = "default"  # Awaiting activation until approved
        user.is_active = False
        user.is_staff = False
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()
        return user
from django import forms
from .models import Qualification, Assessment

class QualificationForm(forms.ModelForm):
    name = forms.CharField(
        label="Qualification Name",
        widget=forms.TextInput(attrs={
            'id': 'qualificationName',
            'class': 'form-control',
            'placeholder': 'e.g. Maintenance Planner',
            'list': 'qualification-options',
            'autocomplete': 'off'
        })
    )
    saqa_id = forms.CharField(
        label="SAQA ID",
        widget=forms.TextInput(attrs={
            'id': 'saqaId',
            'class': 'form-control',
            'placeholder': 'e.g. 101874'
        })
    )

    class Meta:
        model = Qualification
        fields = ['name', 'saqa_id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from . import qualification_registry

        self.registry_entries = qualification_registry.get_entries()
        # Ensure SAQA ID remains read-only for existing instances but editable when adding new ones
        if self.instance and self.instance.pk:
            self.fields['saqa_id'].widget.attrs['readonly'] = True
        else:
            self.fields['saqa_id'].widget.attrs.pop('readonly', None)

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError("Please provide a qualification name.")
        return name

    def save(self, commit=True):
        instance = super().save(commit)
        if commit:
            from . import qualification_registry
            qualification_registry.ensure_entry_from_instance(instance)
        return instance

class AssessmentForm(forms.ModelForm):
    def __init__(self, *args, qualification_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        if qualification_type:
            self.fields['module_number'].choices = \
                Qualification.get_module_choices_for_type(qualification_type)

# ----------------------------------------
# 🔁 Manual Question Entry Form for Builder
# ----------------------------------------
class QuestionBankEntryForm(forms.ModelForm):
    class Meta:
        model = QuestionBankEntry
        fields = ['qualification', 'question_type', 'text', 'marks', 'case_study']
        widgets = {
            'qualification': forms.Select(attrs={'class': 'form-control'}),
            'question_type': forms.Select(attrs={'class': 'form-control'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'marks': forms.NumberInput(attrs={'class': 'form-control'}),
            'case_study': forms.Select(attrs={'class': 'form-control'}),
        }


class AddQuestionToAssessmentForm(forms.Form):
    assessment = forms.ModelChoiceField(queryset=Assessment.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    question = forms.ModelChoiceField(queryset=QuestionBankEntry.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    order = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    marks = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))


from django import forms
from core.models import CustomUser

class AssessmentCenterStudentForm(forms.ModelForm):
    name = forms.CharField(label="Full Name", required=True)
    student_number = forms.CharField(label="Student Number", required=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'student_number']  # Add all fields you'll process

    def clean_student_number(self):
        student_number = self.cleaned_data['student_number']
        if CustomUser.objects.filter(student_number=student_number).exists():
            raise forms.ValidationError("This student number already exists.")
        return student_number

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        student_number = cleaned_data.get('student_number')
        
        # Additional cross-field validation if needed
        return cleaned_data
    

from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import CustomUser

class StudentRegistrationForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'student_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'student_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student Number'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the password field that comes with UserChangeForm
        self.fields.pop('password', None)
