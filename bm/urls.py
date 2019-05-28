from django.urls import path

from bm.views import all_orders

urlpatterns = [
    path('orders', all_orders, name='all_orders'),
]
