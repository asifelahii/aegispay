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
    path("demo/payment/", views.payment_demo, name="payment_demo"),
    path("demo/payment/context/", views.payment_demo_context, name="payment_demo_context"),
    path("demo/payment/result/", views.payment_demo_result, name="payment_demo_result"),
    path("demo/payment/success/", views.payment_demo_success, name="payment_demo_success"),
]
