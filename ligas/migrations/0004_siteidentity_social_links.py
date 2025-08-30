from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ligas', '0003_siteidentity'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteidentity',
            name='facebook_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='siteidentity',
            name='instagram_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='siteidentity',
            name='tiktok_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='siteidentity',
            name='whatsapp_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='siteidentity',
            name='twitter_url',
            field=models.URLField(blank=True),
        ),
    ]

