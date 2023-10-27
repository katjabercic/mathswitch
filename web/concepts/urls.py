from django.urls import path

from . import views

urlpatterns = [
    path("<slug:item_id>/", views.index),
]