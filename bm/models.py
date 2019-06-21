from django.db import models

# Create your models here.


class ParentOrder(models.Model):
    uid = models.CharField(max_length=30, default='')
    name = models.CharField(max_length=200)


class OrderDB(models.Model):
    parentOrder = models.ForeignKey(ParentOrder, on_delete=models.CASCADE)
    orderID = models.CharField(max_length=30, default='')
    ordType = models.CharField(max_length=20, default='')
    ordStatus = models.CharField(max_length=30, default='')
    side = models.CharField(max_length=10)
    price = models.FloatField(null=True, blank=True, default=None)
    timestamp = models.DateTimeField(default=None)
    symbol = models.CharField(max_length=20)
    stopPx = models.FloatField(null=True, blank=True, default=None)
    text = models.CharField(max_length=100, default='')
    ordRejReason = models.CharField(max_length=100, default='')
