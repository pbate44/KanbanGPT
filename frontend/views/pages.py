
import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render

from frontend.forms import ContactForm

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'index.html')

def contact_us(request):
    form = ContactForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        name    = form.cleaned_data['name']
        email   = form.cleaned_data['email']
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']

        body = (
            f"New contact form submission:\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Subject: {subject}\n"
            f"Message: {message}\n"
        )

        recipient = getattr(settings, 'CONTACT_EMAIL', settings.EMAIL_HOST_USER)

        try:
            msg = EmailMessage(
                subject=f"Contact Us Form: {subject}",
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
                reply_to=[email],
            )
            msg.send(fail_silently=False)
        except Exception:
            logger.exception("Failed to send contact form email from %s", email)
            messages.error(request, "Sorry, your message could not be sent. Please try again later.")
            return render(request, 'contact_us.html', {'form': form})

        return redirect('contact_us_success')

    return render(request, 'contact_us.html', {'form': form})

def contact_us_success(request):
    return render(request, "contact_us_success.html")

def about_us(request):
    return render(request, 'about_us.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def terms_of_service(request):
    return render(request, 'terms_of_service.html')

def docs(request):
    return render(request, 'docs.html')
