from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from celery import shared_task
from your_project.settings import EMAIL_HOST_USER
from django.contrib.auth.models import User


@shared_task
def send_welcome_email(user_id):
    user = User.objects.get(id=user_id)
    subject = 'Welcome to Our Website!'
    message = f'Dear {user.username},\n\nThank you for registering with skyloov!'
    from_email = EMAIL_HOST_USER
    recipient_list = [user.email]
    send_mail(subject, message, from_email, recipient_list)
    user.is_sent_welcome_email = True
    user.save()