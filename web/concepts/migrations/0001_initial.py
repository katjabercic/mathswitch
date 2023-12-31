# Generated by Django 4.2.6 on 2023-10-27 11:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=[('Wd', 'Wikidata'), ('nL', 'nLab'), ('WpEN', 'Wikipedia (English)'), ('AUm', 'Agda Unimath')], max_length=4)),
                ('identifier', models.CharField(max_length=200)),
                ('url', models.URLField()),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('links', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='concepts.item')),
            ],
            options={
                'unique_together': {('source', 'identifier')},
            },
        ),
    ]
