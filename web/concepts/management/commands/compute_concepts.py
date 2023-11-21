import logging
from typing import Dict, List

from concepts.models import Concept, Item, Link
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db.utils import IntegrityError


class UnionFind:
    def __init__(self, size):
        self.parent = [i for i in range(size)]
        self.rank = [0] * size

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x != root_y:
            if self.rank[root_x] < self.rank[root_y]:
                self.parent[root_x] = root_y
            elif self.rank[root_x] > self.rank[root_y]:
                self.parent[root_y] = root_x
            else:
                self.parent[root_y] = root_x
                self.rank[root_x] += 1

    def get_components(self):
        components = {}
        for i in range(len(self.parent)):
            root = self.find(i)
            if root not in components:
                components[root] = [i]
            else:
                components[root].append(i)
        return components


class Command(BaseCommand):
    num_to_id: List[str] = []
    id_to_num: Dict[str, int] = {}
    id_to_item: Dict[str, Item] = {}

    def union(self, uf, link: Link):
        uf.union(self.id_to_num[link.source.id], self.id_to_num[link.destination.id])

    def handle(self, *args, **options):
        # all items that do not appear in an edge are components
        singletons = Item.objects.filter(
            incoming_items__isnull=True, outgoing_items__isnull=True
        )
        count_duplicates = 0
        for i in singletons:
            new_concept = Concept(name=i.name, description=i.description)
            try:
                new_concept.save()
            except IntegrityError:
                count_duplicates += 1
                logging.log(
                    logging.WARNING,
                    f" A concept named '{new_concept.name}' already exists.",
                )
            i.concept = new_concept

        print("compute non-singletons")
        # now deal with those that do not have a concept yet
        print(
            Item.objects.filter(
                Q(incoming_items__isnull=False) | Q(outgoing_items__isnull=False)
            ).query
        )
        for i in Item.objects.filter(
            Q(incoming_items__isnull=False) | Q(outgoing_items__isnull=False)
        ):
            self.num_to_id.append(i.id)
            self.id_to_item[i.id] = i
        for i, id in enumerate(self.num_to_id):
            self.id_to_num[id] = i
        uf = UnionFind(len(self.num_to_id))
        for link in Link.objects.all():
            self.union(uf, link)
        for v in uf.get_components().values():
            # first check if WD is one of the items
            items = list(map(lambda i: self.id_to_item[self.num_to_id[i]], v))
            items.sort(key=Item.source_key())
            new_concept = Concept(name=items[0].name, description=items[0].description)
            try:
                new_concept.save()
            except IntegrityError:
                logging.log(
                    logging.WARNING,
                    f" A concept named '{new_concept.name}' already exists.",
                )
                new_concept = Concept.objects.get(name=items[0].name)
            print(f"linking {new_concept.id}")
            for item in items:
                item.concept = new_concept
                item.save()
