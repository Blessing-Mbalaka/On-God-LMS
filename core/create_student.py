from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.models import CustomUser, AssessmentCentre
from core.forms import AssessmentCenterStudentForm
from django.core.mail import send_mail
from django.utils.timezone import now
import random, string

@login_required
def create_student_by_assessment_center(request):
    if request.user.role != 'assessment_center':
        messages.error(request, "You do not have permission to access this page.")
        return redirect('custom_login')

    # Get the assessment center associated with this user
    assessment_center = request.user.assessment_centre
    qualification = None
    
    if assessment_center:
        qualification = assessment_center.qualification_assigned
    else:
        messages.error(request, "Your account is not associated with an assessment center.")
        return redirect('custom_login')  # Or some appropriate redirect

    # Get all students for this assessment center
    students = CustomUser.objects.filter(
        role='learner',
        assessment_centre=assessment_center
    ).order_by('-created_at')

    if request.method == 'POST':
        # Handle status toggle
        if 'toggle_status' in request.POST:
            student_id = request.POST.get('student_id')
            try:
                student = CustomUser.objects.get(
                    id=student_id,
                    assessment_centre=assessment_center
                )
                student.is_active = not student.is_active
                if not student.is_active:
                    student.deactivated_at = now()
                student.save()
                messages.success(request, "Student status updated successfully.")
            except CustomUser.DoesNotExist:
                messages.error(request, "Student not found or not associated with your center.")
            return redirect('create_student_by_assessment_center')
            
        # Handle student creation
        form = AssessmentCenterStudentForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            student_number = form.cleaned_data['student_number']

            first, *last_parts = name.split()
            last = " ".join(last_parts) if last_parts else ""

            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

            try:
                student = CustomUser.objects.create_user(
                    username=email,
                    email=email,
                    first_name=first,
                    last_name=last,
                    role='learner',
                    student_number=student_number, 
                    qualification=qualification,
                    assessment_centre=assessment_center,
                    is_active=True,
                    is_staff=False,
                    activated_at=now()
                )
                
                student.set_password(password)
                student.save()

                send_mail(
                    'Your CHIETA LMS Password',
                    f'Hello {first},\n\nYour account has been created with:\n\n'
                    f'Username: {email}\n'
                    f'Password: {password}\n\n'
                    f'Please log in and change your password immediately.',
                    'noreply@chieta.co.za',
                    [email],
                    fail_silently=True,
                )

                messages.success(request, f"Student {email} created successfully. Login details sent.")
            except IntegrityError:
                messages.error(request, "A student with this email or student number already exists.")
            return redirect('create_student_by_assessment_center')
    else:
        form = AssessmentCenterStudentForm()

    return render(request, 'core/assessment-center/student_manager.html', {
        'form': form,
        'qualification': qualification,
        'assessment_center': assessment_center,
        'students': students,
        'user': request.user
    })

@login_required
def toggle_student_status(request, student_id):
    if request.user.role != 'assessment_center':
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('custom_login')

    assessment_center = AssessmentCentre.objects.filter(name=request.user.first_name).first()
    if not assessment_center:
        messages.error(request, "Assessment center not found.")
        return redirect('create_student_by_assessment_center')

    student = get_object_or_404(
        CustomUser, 
        id=student_id, 
        assessment_center=assessment_center
    )
    student.is_active = not student.is_active
    student.save()

    messages.success(request, "Student status updated successfully.")
    return redirect('create_student_by_assessment_center')