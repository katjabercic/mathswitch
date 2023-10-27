from concepts.models import Item
from django.http import Http404, HttpResponse
from django.template import loader


def index(request, item_id):
    try:
        item = Item.objects.get(identifier=item_id)
    except Item.DoesNotExist:
        raise Http404("Item does not exist")
    template = loader.get_template("detail.html")
    context = {
        "item": {
            "identifier": item.identifier,
            "name": item.name,
            "description": item.description,
            "url": item.url,
        }
    }
    return HttpResponse(template.render(context, request))
