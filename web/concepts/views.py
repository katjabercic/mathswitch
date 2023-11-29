from concepts.models import Concept, Item
from django.shortcuts import get_object_or_404, redirect, render


def concept(request, name):
    concept = get_object_or_404(Concept, name=name)
    context = {
        "concept": {
            "name": concept.name,
            "description": concept.description,
            "items": [
                item.to_dict() for item in Item.objects.filter(concept=concept.id)
            ],
        }
    }
    return render(request, "detail.html", context)


def home(request):
    autocomplete_names = [c.name for c in Concept.objects.all() if c.name is not None]
    context = {
        "concepts": autocomplete_names,
        "number_of_links": {
            "wikidata": Item.objects.filter(source=Item.Source.WIKIDATA).count(),
            "nlab": Item.objects.filter(source=Item.Source.NLAB).count(),
            "mathworld": Item.objects.filter(source=Item.Source.MATHWORLD).count(),
            "agda_unimath": Item.objects.filter(
                source=Item.Source.AGDA_UNIMATH
            ).count(),
        },
    }
    return render(request, "index.html", context)


def search(request):
    search_value = request.GET.get("q")
    return redirect("/concept/" + search_value)


def redirect_item_to_concept(request, source, identifier):
    # should this be a permanent redirect?
    item = get_object_or_404(Item, source=source, identifier=identifier)
    return redirect("/concept/" + item.concept.name)
