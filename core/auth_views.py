# your_app/auth_views.py
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from .models import CustomUser

def send_password_reset_email(user, request):
    # Generate token and uid
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # Create reset link
    reset_url = f"{request.build_absolute_uri('/')[:-1]}/reset-password/{uid}/{token}/"

    # Email content based on user role
    if user.role == 'learner':
        subject = 'Your CHIETA LMS Password Reset'
        greeting = f"Dear {user.first_name or 'Learner'},"
    else:
        subject = 'Your CHIETA Staff Account Password Reset'
        greeting = f"Dear {user.get_role_display()},"

    # Send email
    try:
        send_mail(
            subject,
            f"{greeting}\n\n"
            f"Please click the link to reset your password: {reset_url}\n\n"
            f"This link will expire in 24 hours.\n"
            f"If you didn't request this, please contact support immediately.\n\n"
            f"Best regards,\n"
            f"The CHIETA Team",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        print(
            f"[PasswordResetEmail] Sent reset link to {user.email}: {reset_url}",
            flush=True,
        )
    except Exception as exc:  # pragma: no cover - operational logging
        print(
            f"[PasswordResetEmail] Failed to send reset link to {user.email}: {exc}",
            flush=True,
        )
        raise




def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = CustomUser.objects.filter(email=email).first()
    
        if user:
            # Check if account is active
            if not user.is_active:
                messages.error(request, 'Your account is not active. Please contact support.')
                return redirect('forgot_password')
        
            # Check if account was recently deactivated
            if user.deactivated_at and (timezone.now() - user.deactivated_at).days < 30:
                messages.error(request, 'This account has been deactivated. Please contact support.')
                return redirect('forgot_password')
        
            send_password_reset_email(user, request)
            messages.success(request, 'Password reset link has been sent to your email.')
            return redirect('custom_login')
        else:
            messages.error(request, 'No account found with this email.')

    return render(request, "core/login/forgot_password.html")

def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    # Validate user and token
    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, 'Invalid or expired reset link.')
        return redirect('custom_login')

    # Check if account is active
    if not user.is_active:
        messages.error(request, 'Your account is not active. Please contact support.')
        return redirect('custom_login')

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
    
        if password == confirm_password:
            # Additional password validation can be added here
            if len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                return render(request, "core/login/reset_password.html")
        
            user.set_password(password)
            user.save()
        
            # Log password reset activity
            user.last_updated_at = timezone.now()
            user.save()
        
            messages.success(request, 'Your password has been reset successfully. Please login with your new password.')
            return redirect('custom_login')
        else:
            messages.error(request, 'Passwords do not match.')

    return render(request, "core/login/reset_password.html")
