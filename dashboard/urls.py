from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    path(
        "transactions/<str:transaction_id>/",
        views.transaction_detail,
        name="transaction_detail",
    ),
]
