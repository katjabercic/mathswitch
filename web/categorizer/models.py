from django.db import models


class Item(models.Model):
    """Copy of a concepts.Item, stored in the pgvector DB (no cross-DB FK)."""

    # same value as concepts.Item.id
    id = models.IntegerField(primary_key=True)
    # concepts.Item.identifier
    external_id = models.CharField(max_length=300)
    normalized_name = models.CharField(max_length=300, null=True)
    description = models.TextField(null=True)
    keywords = models.TextField(null=True, blank=True)
