from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.template import loader

from bm.models import OrderDB, ParentOrder

# Create your views here.


def all_orders(request):
    template = loader.get_template('bm/orders.html')
    context = {
        'order_list': OrderDB.objects.all(),
        'column_names': ("Parent", "Name", "Type", "Status", "Side", "Price", "Text", "StopPrice")
    }
    return HttpResponse(template.render(context, request))
