# Generated manually to fix email_id column

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('frontend', '0008_swimlane_card_swimlane'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE frontend_card ADD COLUMN email_id VARCHAR(12) NULL;",
            reverse_sql="ALTER TABLE frontend_card DROP COLUMN email_id;"
        ),
    ]
