# Generated by Django 4.2.6 on 2023-11-23 16:24

from django.db import migrations, models
import django.db.models.functions.text


class Migration(migrations.Migration):
    dependencies = [
        ("concepts", "0007_concept_item_concept"),
    ]

    operations = [
        migrations.AlterField(
            model_name="concept",
            name="name",
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddConstraint(
            model_name="concept",
            constraint=models.UniqueConstraint(
                models.OrderBy(
                    django.db.models.functions.text.Lower("name"), descending=True
                ),
                name="unique_lower_name",
            ),
        ),
    ]
