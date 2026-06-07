
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxLengthValidator
from django.utils import timezone


class Board(models.Model):
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True, validators=[MaxLengthValidator(3000)])
    owner       = models.ForeignKey(User, related_name='boards', on_delete=models.CASCADE)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    image       = models.ImageField(
        upload_to='board_images/', blank=True, null=True,
        help_text='Board image (JPEG, PNG, GIF, WebP - Max 5MB)', max_length=255,
    )

    def __str__(self):
        return self.name


class Column(models.Model):
    board    = models.ForeignKey(Board, related_name='columns', on_delete=models.CASCADE)
    name     = models.CharField(max_length=50)
    position = models.PositiveIntegerField(default=0)
    color    = models.CharField(max_length=32, default="#f1f1f1")

    def __str__(self):
        return f"{self.name} ({self.board.name})"

    class Meta:
        ordering = ['position']


class Swimlane(models.Model):
    board    = models.ForeignKey(Board, related_name='swimlanes', on_delete=models.CASCADE)
    name     = models.CharField(max_length=100, default="New Swimlane")
    position = models.PositiveIntegerField(default=0)
    height   = models.PositiveIntegerField(default=300)

    def __str__(self):
        return f"{self.name} ({self.board.name})"

    class Meta:
        ordering = ['position']


class Card(models.Model):
    column      = models.ForeignKey(Column, related_name='cards', on_delete=models.CASCADE)
    swimlane    = models.ForeignKey(Swimlane, related_name='cards', on_delete=models.CASCADE, null=True, blank=True)
    title       = models.CharField(max_length=100)
    description = models.TextField(blank=True, validators=[MaxLengthValidator(16000)])
    position    = models.PositiveIntegerField(default=0)
    priority    = models.PositiveIntegerField(default=0, choices=[(i, i) for i in range(0, 11)])
    color       = models.CharField(max_length=20, default="#f1f1f1")
    css_class   = models.CharField(max_length=50, blank=True, null=True)
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)
    ai_context            = models.TextField(blank=True, default='')
    ai_context_updated_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.color or self.color == "#f1f1f1":
                self.color     = "rgb(240, 248, 255)"
                self.css_class = "card-color-default"
            elif not self.css_class:
                self.css_class = self.determine_css_class_from_color(self.color)
        super().save(*args, **kwargs)

    @classmethod
    def determine_css_class_from_color(cls, color):
        COLOR_CSS_MAP = {
            'rgb(240, 248, 255)': 'card-color-default',
            'rgb(241, 11, 11)':   'card-color-red',
            'rgb(247, 103, 7)':   'card-color-orange',
            'rgb(247, 243, 11)':  'card-color-yellow',
            'rgb(165, 231, 9)':   'card-color-light-green',
            'rgb(12, 133, 8)':    'card-color-dark-green',
            'rgb(13, 160, 111)':  'card-color-teal',
            'rgb(20, 197, 159)':  'card-color-cyan',
            'rgb(15, 41, 161)':   'card-color-blue',
            'rgb(118, 11, 240)':  'card-color-purple',
            'rgb(194, 8, 178)':   'card-color-magenta',
            'rgb(230, 20, 90)':   'card-color-pink',
            'rgb(2, 9, 15)':      'card-color-dark',
        }
        return COLOR_CSS_MAP.get(color, None)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['position']


class ActivityLog(models.Model):
    content_type   = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id      = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    action_type    = models.CharField(max_length=50)
    message        = models.TextField(blank=True, validators=[MaxLengthValidator(64000)])
    user           = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.content_object} - {self.action_type} at {self.created_at}"


class AIInteraction(models.Model):
    card       = models.ForeignKey(Card, related_name='ai_interactions', on_delete=models.CASCADE)
    question   = models.TextField(validators=[MaxLengthValidator(64000)])
    response   = models.TextField(validators=[MaxLengthValidator(64000)])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI Interaction on {self.card} at {self.created_at}"


class CardLogEntry(models.Model):
    LOG_SOURCES = (
        ('manual', 'Manual'),
        ('email',  'Email'),
        ('ai',     'AI Interaction'),
    )
    card       = models.ForeignKey(Card, related_name='log_entries', on_delete=models.CASCADE)
    text       = models.TextField(validators=[MaxLengthValidator(100000)])
    source     = models.CharField(max_length=20, choices=LOG_SOURCES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source} log for {self.card} at {self.created_at}"


class Subtask(models.Model):
    card        = models.ForeignKey(Card, related_name='subtasks', on_delete=models.CASCADE)
    title       = models.CharField(max_length=100)
    description = models.TextField(blank=True, validators=[MaxLengthValidator(10000)])
    is_complete = models.BooleanField(default=False)
    due_date    = models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class AIChatSession(models.Model):
    card       = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='chat_sessions')
    title      = models.CharField(max_length=255, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Session {self.id} – Card {self.card_id}"


class AIChatMessage(models.Model):
    ROLE_CHOICES = (
        ('system',    'System'),
        ('user',      'User'),
        ('assistant', 'Assistant'),
    )
    card       = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='chat_messages')
    session    = models.ForeignKey(AIChatSession, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content    = models.TextField(validators=[MaxLengthValidator(100000)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role} message for Card {self.card_id}"


class CardAttachment(models.Model):
    card        = models.ForeignKey(Card, related_name='attachments', on_delete=models.CASCADE)
    file        = models.FileField(upload_to='card_attachments/', max_length=255)
    filename    = models.CharField(max_length=255)
    file_type   = models.CharField(max_length=127)
    file_size   = models.IntegerField()
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} ({self.card.title})"

    def get_icon_class(self):
        file_type = self.file_type.lower()
        if 'pdf' in file_type:
            return 'bi-file-pdf'
        elif 'word' in file_type or 'docx' in file_type or 'doc' in file_type:
            return 'bi-file-word'
        elif 'text' in file_type or 'txt' in file_type:
            return 'bi-file-text'
        elif 'csv' in file_type or 'excel' in file_type or 'xlsx' in file_type:
            return 'bi-file-excel'
        return 'bi-file'


class UserProfile(models.Model):
    user                    = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    dark_mode               = models.BooleanField(default=False)
    timezone                = models.CharField(max_length=64, default="UTC")
    language                = models.CharField(max_length=20, default="en")
    email_notifications     = models.BooleanField(default=True)
    marketing_notifications = models.BooleanField(default=False)
    two_factor_enabled      = models.BooleanField(default=False)
    time_format             = models.CharField(max_length=20, default="24-hour")
    ai_chat_always_open     = models.BooleanField(default=False)

    PLAN_FREE    = "free"
    PLAN_PREMIUM = "premium"
    PLAN_CHOICES = [(PLAN_FREE, "Free"), (PLAN_PREMIUM, "Premium")]

    plan                       = models.CharField(max_length=20, choices=PLAN_CHOICES, default=PLAN_FREE)
    stripe_customer_id         = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id     = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_status = models.CharField(max_length=50, blank=True, null=True)
    premium_start_date         = models.DateField(null=True, blank=True)

    ai_model = models.CharField(max_length=150, blank=True, null=True)

    THEME_CHOICES = [
        ('light',  'Light'),
        ('dark',   'Dark'),
        ('system', 'System Default'),
    ]
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='system')

    def is_premium(self) -> bool:
        return self.plan == self.PLAN_PREMIUM and self.stripe_subscription_status in {"active", "trialing"}

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class TwoFactorCode(models.Model):
    user       = models.ForeignKey(User, related_name='two_factor_codes', on_delete=models.CASCADE)
    code       = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used       = models.BooleanField(default=False)

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    def mark_as_used(self):
        self.used = True
        self.save(update_fields=['used'])

    def __str__(self):
        return f"2FA Code for {self.user.username}"
