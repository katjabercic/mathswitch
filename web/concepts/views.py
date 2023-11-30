from concepts.models import Concept, Item
from django.shortcuts import get_object_or_404, redirect, render


def concept(request, name):
    try:
        concept = Concept.objects.get(name=name)
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
    except Concept.DoesNotExist:
        return redirect("/results/" + name)


def home(request):
    autocomplete_names = [c.name for c in Concept.objects.all() if c.name is not None]
    context = {
        "concepts": autocomplete_names,
        "number_of_links": {
            "wikidata": Item.objects.filter(source=Item.Source.WIKIDATA).count(),
            "wikipedia_en": Item.objects.filter(source=Item.Source.WIKIPEDIA_EN).count(),
            "nlab": Item.objects.filter(source=Item.Source.NLAB).count(),
            "mathworld": Item.objects.filter(source=Item.Source.MATHWORLD).count(),
            "proof_wiki": Item.objects.filter(source=Item.Source.PROOF_WIKI).count(),
            "encyclopedia_of_mathematics": Item.objects.filter(
                source=Item.Source.ENCYCLOPEDIA_OF_MATHEMATICS
            ).count(),
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


def results(request, query):
    concepts = Concept.objects.filter(name__contains=query)
    context = {
        "query": query,
        "results": [concept.name for concept in concepts]
        }
    return render(request, "results.html", context)
