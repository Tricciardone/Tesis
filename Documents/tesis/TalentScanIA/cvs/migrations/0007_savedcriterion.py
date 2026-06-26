from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cvs', '0006_cv_pipeline_status_cv_is_shortlisted_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedCriterion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Nombre del criterio')),
                ('criterion_type', models.CharField(choices=[('job_match', 'Matching contra puesto'), ('bulk_analysis', 'Comparativa IA'), ('search', 'Búsqueda de perfiles')], default='job_match', max_length=20, verbose_name='Tipo de criterio')),
                ('content', models.TextField(verbose_name='Contenido del criterio')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Última actualización')),
                ('last_used_at', models.DateTimeField(blank=True, null=True, verbose_name='Último uso')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Criterio guardado',
                'verbose_name_plural': 'Criterios guardados',
                'ordering': ['-updated_at'],
            },
        ),
    ]
