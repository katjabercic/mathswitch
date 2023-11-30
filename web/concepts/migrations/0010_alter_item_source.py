# Generated by Django 4.2.6 on 2023-11-29 21:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("concepts", "0009_alter_item_source"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="source",
            field=models.CharField(
                choices=[
                    ("Wd", "Wikidata"),
                    ("nL", "nLab"),
                    ("MW", "MathWorld"),
                    ("PW", "ProofWiki"),
                    ("EoM", "Encyclopedia of Mathematics"),
                    ("WpEN", "Wikipedia (English)"),
                    ("AUm", "Agda Unimath"),
                ],
                max_length=4,
            ),
        ),
    ]