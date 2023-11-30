from typing import Optional
from concepts.models import Item, Link

WD_OTHER_SOURCES = {
    Item.Source.NLAB: {
        "wd_property": "wdt:P4215",
        "json_key": "nlabID",
    },
    Item.Source.MATHWORLD: {
        "wd_property": "wdt:P2812",
        "json_key": "mwID",
    },
    Item.Source.PROOF_WIKI: {
        "wd_property": "wdt:P6781",
        "json_key": "pwID",
    },
    Item.Source.ENCYCLOPEDIA_OF_MATHEMATICS: {
        "wd_property": "wdt:P7554",
        "json_key": "eomID",
    }
}
# Wikipedia is dealt with elsewhere

class BaseWdRawItem:

    def __init__(self, source, json_item):
        self.source = source
        self.raw = json_item
        self.wd_id = self.raw["item"]["value"]
        self.item = self.get_item()

    def identifier(self):
        pass

    def url(self):
        pass

    def name(self):
        pass

    def description(self):
        return None

    def has_source(self, source):
        if source == Item.Source.WIKIPEDIA_EN:
            return "wp_en" in self.raw
        else:
            return WD_OTHER_SOURCES[source]["json_key"] in self.raw

    def switch_source_to(self, source):
        return BaseWdRawItem.raw_item(source, self.raw)

    def to_item(self) -> Optional[Item]:
        return Item(
            source=self.source,
            identifier=self.identifier(),
            url=self.url(),
            name=self.name(),
            description=self.description(),
        )

    def _get_item_queryset(self):
        return Item.objects.filter(source=self.source, identifier=self.identifier())

    def item_exists(self):
        return self._get_item_queryset().exists()
    
    def get_item(self) -> Optional[Item]:
        return self._get_item_queryset().first()
    
    def yield_switched_if_not_exists(self, source):
        switched = self.switch_source_to(source)
        if not switched.item_exists():
            yield switched.to_item()
    
    def save_link_to(self, source):
        target = self.switch_source_to(source)
        if target is not None: 
            destinationItem = target.get_item()
            if self.item is not None and destinationItem is not None:
                Link.save_new(self.item, destinationItem, Link.Label.WIKIDATA)

    def save_links(self):
        # always save a link to the Wikipedia item
        if self.has_source(Item.Source.WIKIPEDIA_EN):
            self.save_link_to(Item.Source.WIKIPEDIA_EN)

    @staticmethod
    def raw_item(source, json_item):
        match source:
            case Item.Source.WIKIDATA:
                return WdRawItem(json_item)
            case Item.Source.NLAB:
                return nLabRawItem(json_item)
            case Item.Source.MATHWORLD:
                return MWRawItem(json_item)
            case Item.Source.PROOF_WIKI:
                return PWRawItem(json_item)
            case Item.Source.ENCYCLOPEDIA_OF_MATHEMATICS:
                return EoMRawItem(json_item)
            case Item.Source.WIKIPEDIA_EN:
                return WpENRawItem(json_item)


class WdRawItem(BaseWdRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.WIKIDATA, json_item)

    def identifier(self):
        return self.wd_id.split("/")[-1]

    def url(self):
        return self.wd_id

    def name(self):
        if "itemLabel" in self.raw:
            return self.raw["itemLabel"]["value"]
        else:
            return None

    def description(self):
        if "itemDescription" in self.raw:
            return self.raw["itemDescription"]["value"]
        else:
            return None

    def save_links(self):
        super().save_links()
        for source in WD_OTHER_SOURCES:
            if self.has_source(source):
                self.save_link_to(source)

class WpENRawItem(BaseWdRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.WIKIPEDIA_EN, json_item)

    def identifier(self):
        return self.url().split("/")[-1]

    def url(self):
        return self.raw["wp_en"]["value"]

    def name(self):
        return self.identifier()


class OtherWdRawItem(BaseWdRawItem):
    def __init__(self, source, json_item):
        super().__init__(source, json_item)

    def identifier(self):
        json_key = WD_OTHER_SOURCES[self.source]["json_key"]
        return self.raw[json_key]["value"]

    def name(self):
        return self.identifier()

    def save_links(self):
        super().save_links()
        # link back to WD items
        self.save_link_to(WdRawItem(self.raw))

class nLabRawItem(OtherWdRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.NLAB, json_item)

    def url(self):
        return "https://ncatlab.org/nlab/show/" + self.identifier()


class MWRawItem(OtherWdRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.MATHWORLD, json_item)

    def url(self):
        return "https://mathworld.wolfram.com/" + self.identifier() + ".html"


class PWRawItem(OtherWdRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.PROOF_WIKI, json_item)

    def url(self):
        return "https://proofwiki.org/wiki/" + self.identifier()


class EoMRawItem(OtherWdRawItem):
    def __init__(self, json_item):
        super().__init__(Item.Source.ENCYCLOPEDIA_OF_MATHEMATICS, json_item)

    def url(self):
        return "https://encyclopediaofmath.org/wiki/" + self.identifier()