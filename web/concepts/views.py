from concepts.models import Item
from django.shortcuts import get_object_or_404, render


def index(request, item_id):
    item = get_object_or_404(Item, identifier=item_id)
    context = {
        "item": {
            "identifier": item.identifier,
            "name": item.name,
            "description": item.description,
            "url": item.url,
            "links": item.get_links()
        }
    }
    return render(request, "detail.html", context)
