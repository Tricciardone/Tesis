from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cvs', '0005_analysisquery_detected_education_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cv',
            name='pipeline_status',
            field=models.CharField(
                choices=[
                    ('new', 'Nuevo'),
                    ('review', 'Revisar'),
                    ('shortlist', 'Shortlist'),
                    ('interview', 'Entrevista'),
                    ('discarded', 'Descartado'),
                ],
                default='new',
                max_length=20,
                verbose_name='Estado de selección',
            ),
        ),
        migrations.AddField(
            model_name='cv',
            name='is_shortlisted',
            field=models.BooleanField(default=False, verbose_name='En shortlist'),
        ),
        migrations.AddField(
            model_name='cv',
            name='recruiter_notes',
            field=models.TextField(blank=True, null=True, verbose_name='Notas internas del recruiter'),
        ),
    ]
