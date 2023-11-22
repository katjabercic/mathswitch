import logging

from concepts.utils import UnionFind
from django.db import models
from django.db.utils import IntegrityError


class Concept(models.Model):
    name = models.CharField(max_length=200, null=True, unique=True)
    description = models.TextField(null=True)

    class Meta:
        ordering = ["name", "description"]


class LinkQuerySet(models.QuerySet):
    def to_tuples(self):
        for link in self:
            yield (link.source, link.destination)


class ItemQuerySet(models.QuerySet):
    def create_singleton_concepts(self):
        count_duplicates = 0
        for item in self:
            new_concept = Concept(name=item.name, description=item.description)
            try:
                new_concept.save()
            except IntegrityError:
                count_duplicates += 1
                logging.log(
                    logging.WARNING,
                    f" A concept named '{new_concept.name}' already exists.",
                )
            item.concept = new_concept

    def create_concepts(self):
        uf = UnionFind(self.all(), Link.objects.all().to_tuples())
        for concept_items in uf.get_item_components(sort_key=Item.Source.key()):
            # first check if WD is one of the items
            new_concept = Concept(
                name=concept_items[0].name, description=concept_items[0].description
            )
            if new_concept.name == "Alexander polynomial":
                print(concept_items)
            try:
                new_concept.save()
            except IntegrityError:
                logging.log(
                    logging.WARNING,
                    f" A concept named '{new_concept.name}' already exists.",
                )
                new_concept = Concept.objects.get(name=concept_items[0].name)
            # print(f"linking {new_concept.id}")
            for item in concept_items:
                item.concept = new_concept
                item.save()


class Item(models.Model):
    class Source(models.TextChoices):
        WIKIDATA = "Wd", "Wikidata"
        NLAB = "nL", "nLab"
        MATHWORLD = "MW", "MathWorld"
        WIKIPEDIA_EN = "WpEN", "Wikipedia (English)"
        AGDA_UNIMATH = "AUm", "Agda Unimath"

        @staticmethod
        def key():
            SOURCES = [
                Item.Source.WIKIDATA,
                Item.Source.NLAB,
                Item.Source.MATHWORLD,
                Item.Source.WIKIPEDIA_EN,
                Item.Source.AGDA_UNIMATH,
            ]
            return lambda item: SOURCES.index(item.source)

    source = models.CharField(max_length=4, choices=Source.choices)
    identifier = models.CharField(max_length=200)
    url = models.URLField(max_length=200)
    name = models.CharField(max_length=200, null=True)
    description = models.TextField(null=True)
    concept = models.ForeignKey(
        Concept,
        models.SET_NULL,
        blank=True,
        null=True,
    )
    objects = ItemQuerySet.as_manager()

    class Meta:
        ordering = ["name", "source", "identifier"]
        unique_together = ["source", "identifier"]

    def to_dict(self):
        return {"name": self.name, "source": self.get_source_display(), "url": self.url}

    def get_linked_items(self):
        linked_destinations = Link.objects.filter(source=self.id).map(
            lambda link: link.destination
        )
        linked_sources = Link.objects.filter(destination=self.id).map(
            lambda link: link.source
        )
        return set(linked_sources + linked_destinations)

    def get_linked_item_urls(self):
        return [i.get_url() for i in self.get_linked_items()]

    def __str__(self):
        if self.name:
            return f"{self.get_source_display()}: {self.identifier} ({self.name})"
        else:
            return f"{self.get_source_display()}: {self.identifier}"


class Link(models.Model):
    class Label(models.TextChoices):
        WIKIDATA = "Wd", "Wikidata"
        AGDA_UNIMATH = "AUm", "Agda Unimath"
        NAME_EQ = "eq", "same name"

    source = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name="outgoing_items"
    )
    destination = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name="incoming_items"
    )
    label = models.CharField(max_length=4, choices=Label.choices)
    objects = LinkQuerySet.as_manager()

    class Meta:
        ordering = ["source", "destination", "label"]
        unique_together = ["source", "destination", "label"]

    @staticmethod
    def save_new(source: Item, destination: Item, label: Label):
        try:
            new_link = Link.objects.create(
                source=source, destination=destination, label=label
            )
            new_link.save()
        except IntegrityError:
            logging.log(
                logging.WARNING,
                f" Link from {source} to {destination} repeated in {label}.",
            )

    def __str__(self):
        return f"{self.source} -[{self.get_label_display()}]-> {self.destination}"
