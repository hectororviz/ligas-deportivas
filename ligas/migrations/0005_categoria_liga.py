from django.db import migrations, models
import django.db.models.deletion


def move_categoria_to_liga(apps, schema_editor):
    Categoria = apps.get_model('ligas', 'Categoria')
    for cat in Categoria.objects.all():
        # categoria has both fields at this point
        liga_id = None
        if hasattr(cat, 'torneo_id') and cat.torneo_id:
            Torneo = apps.get_model('ligas', 'Torneo')
            try:
                torneo = Torneo.objects.get(pk=cat.torneo_id)
                liga_id = torneo.liga_id
            except Torneo.DoesNotExist:
                liga_id = None
        if liga_id is not None:
            cat.liga_id = liga_id
            cat.save(update_fields=['liga_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('ligas', '0004_siteidentity_social_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoria',
            name='liga',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='categorias', to='ligas.liga'),
        ),
        migrations.RunPython(move_categoria_to_liga, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='categoria',
            name='liga',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categorias', to='ligas.liga'),
        ),
        migrations.AlterUniqueTogether(
            name='categoria',
            unique_together={('liga', 'nombre')},
        ),
        migrations.RemoveField(
            model_name='categoria',
            name='torneo',
        ),
    ]

