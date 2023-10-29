from django.db import models


class Item(models.Model):
    class Source(models.TextChoices):
        WIKIDATA = "Wd", "Wikidata"
        NLAB = "nL", "nLab"
        WIKIPEDIA_EN = "WpEN", "Wikipedia (English)"
        AGDA_UNIMATH = "AUm", "Agda Unimath"

    source = models.CharField(max_length=4, choices=Source.choices)
    identifier = models.CharField(max_length=200)
    url = models.URLField(max_length=200)
    name = models.CharField(max_length=200, null=True)
    description = models.TextField(null=True)
    links = models.ManyToManyField("self", blank=True)

    class Meta:
        ordering = ["name", "source", "identifier"]
        unique_together = ["source", "identifier"]

    def get_link(self):
        return {
            "name": self.name,
            "source": self.source,
            "url": self.url
        }

    def get_links(self):
        return [linked_item.get_link() for linked_item in self.links.all()]

    def __str__(self):
        if self.name:
            return f"{self.get_source_display()}: {self.identifier} ({self.name})"
        else:
            return f"{self.get_source_display()}: {self.identifier}"
