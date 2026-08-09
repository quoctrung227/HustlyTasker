from django.db import models

from apps.common.models import BaseModel
from apps.clients.models import Client



class Invoice(BaseModel):

    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        SENT = "SENT"
        PAID = "PAID"
        OVERDUE = "OVERDUE"
        CANCELLED = "CANCELLED"


    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="invoices"
    )


    invoice_number = models.CharField(
        max_length=50,
        unique=True
    )


    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )


    due_date = models.DateField(
        null=True,
        blank=True
    )


    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )


    def __str__(self):
        return self.invoice_number



class Payment(BaseModel):

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments"
    )


    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    payment_method = models.CharField(
        max_length=50
    )


    paid_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return f"Payment {self.amount}"