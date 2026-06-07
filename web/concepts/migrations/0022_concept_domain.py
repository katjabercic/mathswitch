from django.db import migrations, models


def backfill_concept_domain(apps, schema_editor):
    Concept = apps.get_model("concepts", "Concept")
    Item = apps.get_model("concepts", "Item")
    for concept in Concept.objects.all():
        first_item = (
            Item.objects.filter(concept=concept).exclude(domain="").first()
        )
        if first_item and first_item.domain:
            concept.domain = first_item.domain
            concept.save(update_fields=["domain"])


class Migration(migrations.Migration):

    dependencies = [
        ("concepts", "0021_alter_item_identifier_alter_item_name_alter_item_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="concept",
            name="domain",
            field=models.CharField(
                choices=[("math", "Mathematics"), ("phys", "Physics")],
                default="math",
                max_length=4,
            ),
        ),
        migrations.RunPython(backfill_concept_domain, lambda *_args: None),
    ]
