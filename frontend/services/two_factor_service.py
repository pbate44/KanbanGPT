
import random
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from frontend.models import TwoFactorCode


class TwoFactorService:

    @staticmethod
    def generate_code(length=6):
        return "".join(str(random.randint(0, 9)) for _ in range(length))
    
    @staticmethod
    def create_and_send_code(user):
        code = TwoFactorService.generate_code()

        expires_at = timezone.now() + timedelta(minutes=10)
        two_factor_code = TwoFactorCode.objects.create(
            user=user,
            code=code,
            expires_at=expires_at
        )

        subject = "Your login verification code"
        message = (
            f"Hi {user.username},\n\n"
            f"Your verification code is: {code}\n"
            f"This code will expire in 10 minutes.\n\n"
            "If you did not try to log in, you can ignore this email."
        )

        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            return True, code
        except Exception as e:
            print(f"Error sending two-factor code email: {e}")
            return False, None