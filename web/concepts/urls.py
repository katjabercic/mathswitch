from django.urls import path

from . import views

urlpatterns = [
    path("<slug:source>/<slug:identifier>", views.redirect_item_to_concept),
    path("<str:name>/", views.concept),
]
