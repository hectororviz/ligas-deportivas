from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('ligas', '0002_alter_arbitro_options_alter_categoria_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteIdentity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_title', models.CharField(default='Sistema de Ligas', max_length=80)),
                ('sidebar_bg', models.CharField(default='#111827', max_length=7, validators=[django.core.validators.RegexValidator(message='Debe ser un color HEX válido, ej: #111827 o #2563eb', regex='^#(?:[0-9a-fA-F]{3}){1,2}$')])),
                ('accent_color', models.CharField(default='#2563eb', max_length=7, validators=[django.core.validators.RegexValidator(message='Debe ser un color HEX válido, ej: #111827 o #2563eb', regex='^#(?:[0-9a-fA-F]{3}){1,2}$')])),
                ('logo_url', models.URLField(blank=True, help_text='URL de la imagen (max 300x300).')),
            ],
            options={
                'verbose_name': 'Identidad del sitio',
                'verbose_name_plural': 'Identidad del sitio',
            },
        ),
    ]

