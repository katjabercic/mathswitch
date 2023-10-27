from django.db import models

class Item(models.Model):

    class Source(models.TextChoices):
        WIKIDATA = 'Wd', 'Wikidata'
        NLAB = 'nL', 'nLab'
        WIKIPEDIA_EN = 'WpEN', 'Wikipedia (English)'
        AGDA_UNIMATH = 'AUm', 'Agda Unimath'

    source = models.CharField(max_length=4, choices=Source.choices)
    identifier = models.CharField(max_length=200)
    url = models.URLField(max_length=200)
    name = models.CharField(max_length=200, null=True)
    description = models.TextField(null=True)
    links = models.ManyToManyField('self', blank=True)

    class Meta:
        unique_together = ['source', 'identifier']