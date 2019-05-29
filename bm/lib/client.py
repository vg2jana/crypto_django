import bitmex
import logging
import time


class RestClient():

    def __init__(self, test, key, secret, symbol):
        self.api = None
        self.symbol = symbol
        self.test = test
        self.key = key
        self.secret = secret
        self.logger = logging.getLogger()

    def connect_api(self):
        while True:
            self.logger.info('Attempting to connect to REST Client')
            try:
                self.api = bitmex.bitmex(test=self.test, api_key=self.key, api_secret=self.secret)
                break
            except Exception as e:
                self.logger.warning(e)
            time.sleep(1)
        self.logger.info('Connected to REST Client')

    def newOrder(self, **kwargs):

        kwargs['symbol'] = self.symbol
        order = None

        try:
            order, response = self.api.Order.Order_new(**kwargs).result()
        except Exception as e:
            self.logger.warning(e)
            self.logger.warning("Failed to place order with params: {}".format(kwargs))
        else:
            if response.status_code != 200:
                self.logger.warning("Failed to place order with params: {}".format(kwargs))
                self.logger.warning("Status code: {}, Reason: {}".format(response.status_code, response.reason))
                self.logger.warning ("Order: {}".format(order))
                order = None

        return order

    def cancelOrder(self, **kwargs):

        order = None

        try:
            order, response = self.api.Order.Order_cancel(**kwargs).result()
        except Exception as e:
            self.logger.warning(e)
            self.logger.warning("Failed to cancel order with params: {}".format(kwargs))
        else:
            if response.status_code != 200:
                self.logger.warning("Failed to cancel order with params: {}".format(kwargs))
                self.logger.warning("Status code: {}, Reason: {}".format(response.status_code, response.reason))
                self.logger.warning ("Order: {}".format(order))
                order = None

        return order

    def getOrder(self, **kwargs):

        order = None

        try:
            order, response = self.api.Order.getOrders(**kwargs).result()
        except Exception as e:
            self.logger.warning(e)
            self.logger.warning("Failed to cancel order with params: {}".format(kwargs))
        else:
            if response.status_code != 200:
                self.logger.warning("Failed to cancel order with params: {}".format(kwargs))
                self.logger.warning("Status code: {}, Reason: {}".format(response.status_code, response.reason))
                self.logger.warning ("Order: {}".format(order))
                order = None

        if order is not None and len(order) > 0:
            order = order[0]

        return order

    def openOrders(self):

        orders = None

        try:
            orders, response = self.api.Order.Order_getOrders(filter='{"open": true}').result()
        except Exception as e:
            self.logger.warning(e)
            self.logger.warning("Failed to fetch open orders")
        else:
            if response.status_code != 200:
                self.logger.warning("Failed to fetch open orders")
                self.logger.warning("Status code: {}, Reason: {}".format(response.status_code, response.reason))
                orders = None

        return orders
