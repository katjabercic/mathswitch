from django.urls import path

from . import views

urlpatterns = [
    path("<slug:source>/<slug:item_id>/", views.concept),
]
