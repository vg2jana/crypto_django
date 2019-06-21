import logging
import time


class Order:

    def __init__(self, user):

        self.logging = logging.getLogger()
        self.ws = user.ws
        self.client = user.client
        self.orderID = None
        self.orderQty = None
        self.orderType = None
        self.side = None
        self.price = None
        self.execInst = None
        self.ordStatus = None
        self.text = None
        self.timestamp = None
        self.execType = None
        self.cumQty = None
        self.workingIndicator = None
        self.parent_order = user.parent_order

    def get_status(self):

        executions = [o for o in self.ws.ws.data['execution'] if o['orderID'] in self.orderID]

        if len(executions) < 1:
            return

        for k, v in executions[-1]:
            if hasattr(self, k):
                setattr(self, k, v)

    def wait_for_status(self, *status):

        while True:
            self.get_status()
            if self.ordStatus in status:
                break

    def new(self, **kwargs):
        order = self.client.new_order(kwargs)

        if order is None:
            return None

        self.wait_for_status('New', 'Filled', 'PartiallyFilled', 'Canceled')

        return order

    def amend(self, **kwargs):

        order = self.client.amend_order(kwargs)

        if order is None:
            return None

        self.wait_for_status('New', 'Filled', 'PartiallyFilled', 'Canceled')

        return order

    def cancel(self, **kwargs):

        order = self.client.new_order(kwargs)

        if order is None:
            return None

        self.wait_for_status('Canceled')

        return order
