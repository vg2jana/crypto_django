import bitmex

class RestClient():

    def __init__(self, test, key, secret, symbol):
        self.api = bitmex.bitmex(test=test, api_key=key, api_secret=secret)
        self.symbol = symbol

    def exec_api(self, target, *args, **kwargs):

        try:
            return getattr(self.api, target)(args, kwargs)
        except Exception as e:
            print(e)
            print("Error when executing API: {}, arguments={}, kwarguments={}".format(target, args, kwargs))

        return None

    def newOrder(self, **kwargs):

        kwargs['symbol'] = self.symbol
        order = None

        try:
            order, response = self.api.Order.Order_new(**kwargs).result()
        except Exception as e:
            print(e)
            print("Failed to place order with params: {}".format(kwargs))
        else:
            if response.status_code != 200:
                print("Failed to place order with params: {}".format(kwargs))
                print("Status code: {}, Reason: {}".format(response.status_code, response.reason))
                print ("Order: {}".format(order))
                order = None

        return order

    def cancelOrder(self, **kwargs):

        order = None

        try:
            order, response = self.api.Order.Order_cancel(**kwargs).result()
        except Exception as e:
            print(e)
            print("Failed to cancel order with params: {}".format(kwargs))
        else:
            if response.status_code != 200:
                print("Failed to cancel order with params: {}".format(kwargs))
                print("Status code: {}, Reason: {}".format(response.status_code, response.reason))
                print ("Order: {}".format(order))
                order = None

        return order

    def getOrder(self, **kwargs):

        order = None

        try:
            order, response = self.api.Order.getOrders(**kwargs).result()
        except Exception as e:
            print(e)
            print("Failed to cancel order with params: {}".format(kwargs))
        else:
            if response.status_code != 200:
                print("Failed to cancel order with params: {}".format(kwargs))
                print("Status code: {}, Reason: {}".format(response.status_code, response.reason))
                print ("Order: {}".format(order))
                order = None

        if order is not None and len(order) > 0:
            order = order[0]

        return order

    def openOrders(self):

        orders = None

        try:
            orders, response = self.api.Order.Order_getOrders(filter='{"open": true}').result()
        except Exception as e:
            print(e)
            print("Failed to fetch open orders")
        else:
            if response.status_code != 200:
                print("Failed to fetch open orders")
                print("Status code: {}, Reason: {}".format(response.status_code, response.reason))
                orders = None

        return orders
