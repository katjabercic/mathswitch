from concepts.models import Concept, Item
from concepts.utils import normalize_concept_name
from django.shortcuts import get_object_or_404, redirect, render

from web.settings import UI_DOMAINS


def _concepts_in_scope():
    return Concept.objects.filter(domain__in=UI_DOMAINS)


def _items_in_scope():
    return Item.objects.filter(domain__in=UI_DOMAINS)


def concept(request, name):
    try:
        concept = _concepts_in_scope().get(normal_name=name)
        context = {
            "concept": {
                "normal_name": concept.normal_name,
                "display_name": concept.display_name,
                "description": concept.description,
                "items": [
                    item.to_dict()
                    for item in _items_in_scope().filter(concept=concept.id)
                ],
            }
        }
        return render(request, "detail.html", context)
    except Concept.DoesNotExist:
        return redirect("/results/" + name)


def home(request):
    autocomplete_names = [
        c.display_name for c in _concepts_in_scope() if c.normal_name is not None
    ]
    items = _items_in_scope()
    context = {
        "concepts": autocomplete_names,
        "number_of_links": {
            "wikidata": items.filter(source=Item.Source.WIKIDATA).count(),
            "wikipedia_en": items.filter(source=Item.Source.WIKIPEDIA_EN).count(),
            "nlab": items.filter(source=Item.Source.NLAB).count(),
            "mathworld": items.filter(source=Item.Source.MATHWORLD).count(),
            "proof_wiki": items.filter(source=Item.Source.PROOF_WIKI).count(),
            "encyclopedia_of_mathematics": items.filter(
                source=Item.Source.ENCYCLOPEDIA_OF_MATHEMATICS
            ).count(),
            "agda_unimath": items.filter(source=Item.Source.AGDA_UNIMATH).count(),
            "lmfdb": items.filter(source=Item.Source.LMFDB).count(),
        },
    }
    return render(request, "index.html", context)


def search(request):
    search_value = request.GET.get("q") or ""
    return redirect("/concept/" + normalize_concept_name(search_value))


def redirect_item_to_concept(request, source, identifier):
    # should this be a permanent redirect?
    item = get_object_or_404(_items_in_scope(), source=source, identifier=identifier)
    return redirect("/concept/" + item.concept.normal_name)


def results(request, query):
    normalized = normalize_concept_name(query)
    concepts = _concepts_in_scope().filter(normal_name__contains=normalized)
    context = {
        "query": query,
        "results": [
            {"normal_name": concept.normal_name, "display_name": concept.display_name}
            for concept in concepts
        ],
    }
    return render(request, "results.html", context)
