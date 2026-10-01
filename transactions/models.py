from django.db import models


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        P2P = "P2P", "Person to Person"
        CASH_IN = "CASH_IN", "Cash In"
        CASH_OUT = "CASH_OUT", "Cash Out"
        MERCHANT_PAYMENT = "MERCHANT_PAYMENT", "Merchant Payment"
        BILL_PAYMENT = "BILL_PAYMENT", "Bill Payment"

    transaction_id = models.CharField(max_length=64, unique=True)

    sender_id = models.CharField(max_length=64)
    recipient_id = models.CharField(max_length=64)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    transaction_type = models.CharField(
        max_length=32,
        choices=TransactionType.choices,
        default=TransactionType.P2P,
    )

    occurred_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"