from django.core.management.base import BaseCommand
from frontend.services.email_service import EmailProcessor

class Command(BaseCommand):
    help = 'Process emails from ZohoMail and add them to cards'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting email processing...'))
        processor = EmailProcessor()
        processor.fetch_and_process_emails()
        self.stdout.write(self.style.SUCCESS('Successfully processed emails'))