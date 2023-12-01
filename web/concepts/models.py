import logging

from concepts.utils import UnionFind
from django.db import models
from django.db.models.functions import Lower
from django.db.utils import IntegrityError


class Concept(models.Model):
    name = models.CharField(max_length=200, null=True)
    description = models.TextField(null=True)

    class Meta:
        ordering = ["name", "description"]
        constraints = [
            models.UniqueConstraint(Lower("name").desc(), name="unique_lower_name")
        ]


class LinkQuerySet(models.QuerySet):
    def to_tuples(self):
        for link in self:
            yield (link.source, link.destination)


class ItemQuerySet(models.QuerySet):
    def create_singleton_concepts(self):
        for item in self:
            try:
                new_concept = item.to_concept()
                new_concept.save()
            except IntegrityError:
                logging.log(
                    logging.WARNING,
                    f" A concept named '{new_concept.name}' already exists.",
                )
                new_concept = Concept.objects.get(name__iexact=new_concept.name)
            item.concept = new_concept
            item.save()

    def create_concepts(self):
        def take_first(lst):
            return next(filter(lambda x: x is not None, lst), None)

        components = UnionFind(self.all(), Link.objects.all().to_tuples())
        for concept_items in components.get_item_components(sort_key=Item.Source.key()):
            name = take_first([item.name for item in concept_items])
            description = take_first([item.description for item in concept_items])
            new_concept = Concept(name=name, description=description)
            try:
                new_concept.save()
            except IntegrityError:
                logging.log(
                    logging.WARNING,
                    f" A concept named '{new_concept.name}' already exists.",
                )
                new_concept = Concept.objects.get(name=name)
            for item in concept_items:
                item.concept = new_concept
                item.save()


class Item(models.Model):
    class Source(models.TextChoices):
        WIKIDATA = "Wd", "Wikidata"
        NLAB = "nL", "nLab"
        MATHWORLD = "MW", "MathWorld"
        PROOF_WIKI = "PW", "ProofWiki"
        ENCYCLOPEDIA_OF_MATHEMATICS = "EoM", "Encyclopedia of Mathematics"
        WIKIPEDIA_EN = "WpEN", "Wikipedia (English)"
        AGDA_UNIMATH = "AUm", "Agda Unimath"

        @staticmethod
        def key():
            SOURCES = [
                Item.Source.WIKIDATA,
                Item.Source.WIKIPEDIA_EN,
                Item.Source.NLAB,
                Item.Source.MATHWORLD,
                Item.Source.PROOF_WIKI,
                Item.Source.ENCYCLOPEDIA_OF_MATHEMATICS,
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

    def to_concept(self):
        return Concept(name=self.name, description=self.description)

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
                logging.INFO,
                f" Link from {source} to {destination} repeated in {label}.",
            )

    def __str__(self):
        return f"{self.source} -[{self.get_label_display()}]-> {self.destination}"
