import time
import uuid
import logging

from datetime import datetime
from bm.models import OrderDB
from bm.lib.mywebsocket import MyWebSocket
from bm.lib.opportunity import Opportunity
from bm.lib.rest import RestClient
from bm.lib.order import Order
from bm.lib.steps import *


class User:

    def __init__(self, key, secret, symbol, endpoint, dry_run=True):

        self.logger = logging.getLogger()
        self.order_attrs = [f.name for f in OrderDB._meta.get_fields()]
        self.endpoint = endpoint
        self.key = key
        self.secret = secret
        self.symbol = symbol
        self.ws = MyWebSocket(endpoint, symbol, key, secret)
        self.client = RestClient(dry_run, key, secret, symbol)
        self.opportunity = Opportunity(self.ws, self.client)
        self.parent_order = None
        self.tick_size = self.get_tick_size()
        self.num_decimals = self.get_num_decimals()

    def get_num_decimals(self):

        decimals = {
            'XBTUSD': 1
        }

        return decimals[self.symbol]

    def get_tick_size(self):

        ticks = {
            'XBTUSD': 0.5
        }

        return ticks[self.symbol]

    def diff_ticks(self, price, base=None):

        if base is None:
            base = self.ws.ltp()

        return (base - price) / self.tick_size

    def record_order(self, **kwargs):

        kwargs["symbol"] = self.symbol
        kwargs["ordStatus"] = kwargs.get("ordStatus", "New")
        kwargs["parentOrder"] = self.parent_order
        kwargs = {k: v for k, v in kwargs.items() if k in self.order_attrs}
        order = OrderDB.objects.create(**kwargs)
        self.logger.info("NEW Type: {}, Text: {}, Status: {}, Side: {}, Price: {}".format(order.ordType, order.text,
                         order.ordStatus, order.side, order.price))
        return order

    def update_order(self, **kwargs):

        self.logger.info(kwargs)
        order_id = kwargs.pop('orderID')
        self.client.get_order(orderID=order_id)

        order = OrderDB.objects.filter(orderID__exact=order_id).first()
        for k, v in kwargs.items():
            order.__setattr__(k, v)

        self.logger.info("UPDATE Type: {}, Text: {}, Status: {}, Side: {}, Price: {}".format(order.ordType, order.text,
                         order.ordStatus, order.side, order.price))
        order.save()
        return order

    def wait_for_execution(self, orderIDs, wait=False, status=('Canceled', 'Filled')):
        if type(orderIDs) is str:
            orderIDs = [orderIDs, ]

        executions = [o for o in self.ws.ws.data['execution'] if o['orderID'] in orderIDs]

        order_status = None
        while order_status is None:
            for e in executions:
                if e['ordStatus'] in status:
                    order_status = e
                    break

            if wait is False:
                break

        return order_status

    def make_first_order(self, side, qty, price):

        order_status = None
        first_order = None
        while order_status is None:
            if first_order is None:
                while True:
                    first_order = self.client.new_order(orderQty=qty, ordType="Limit", side=side,
                                                       price=price, execInst="ParticipateDoNotInitiate")
                    if first_order is not None:
                        break
                first_order['text'] = 'First order'
                first_order = self.record_order(**first_order)

            # order_status = self.client.getOrder(filter='{"orderID": "%s"}' % first_order.orderID)
            order_status = self.wait_for_execution(first_order.orderID)

            # time_diff = datetime.utcnow() - first_order.timestamp.replace(tzinfo=None)
            ticker = self.ws.ticker()
            if ticker is None:
                continue

            if order_status is None and abs(ticker['last'] - first_order.price) > 5:
                order_status = self.client.cancel_order(orderID=first_order.orderID)
                self.update_order(**order_status)
                first_order = None
                order_status = None

        return self.update_order(**order_status)

    def move_and_fill(self, side, qty, limit_price):

        order = None
        while True:
            bid_ask = self.ws.bid_ask()
            if side == 'Buy':
                price = bid_ask['bid']['price'][0]
            else:
                price = bid_ask['ask']['price'][0]

            if (side == 'Buy' and price > limit_price) or (side == 'Sell' and price < limit_price):
                if order is not None:
                    order.cancel()
                    time.sleep(1)
                break

            if order is None:
                order = Order(self)
                status = order.new(orderQty=qty, ordType="Limit", side=side, price=price,
                                         execInst="ParticipateDoNotInitiate")

                if status is None:
                    order = None
                    continue

            order.get_status()

            if order.ordStatus in ('Filled',):
                break

            elif order.ordStatus == 'Canceled':
                qty -= order.cumQty
                order = None
                continue

            if abs(self.diff_ticks(order.price)) > 10:
                order.cancel()
                time.sleep(1)

        return order

    def worker_incremental_order(self, qty, first_order=None, incremental_tick=20):

        if first_order is None:
            while True:

                if first_order is None:
                    side = self.opportunity.buy_or_sell()
                    bid_ask = self.ws.bid_ask()

                    if side == 'Buy':
                        price = bid_ask['bid']['price'][0]
                    else:
                        price = bid_ask['ask']['price'][0]

                    first_order = Order(self)
                    status = first_order.new(orderQty=qty, ordType="Limit", side=side, price=price,
                                             execInst="ParticipateDoNotInitiate")

                    if status is None:
                        first_order = None
                        continue

                first_order.get_status()

                if first_order.ordStatus in ('Filled',):
                    break

                elif first_order.ordStatus == 'Canceled':
                    if first_order.cumQty > 0:
                        break
                    first_order = None
                    time.sleep(1)
                    continue

                if abs(self.diff_ticks(first_order.price)) > 10:
                    first_order.cancel()
                    time.sleep(1)

            first_order.get_status()

        side = first_order.side
        if side == 'Buy':
            cross_side = 'Sell'
            cross_indicator = 1
            ally_indicator = -1
        else:
            cross_side = 'Buy'
            cross_indicator = -1
            ally_indicator = 1

        # Place first cross order
        while True:

            cross_order = Order(self)
            cross_price = first_order.price + (incremental_tick * self.tick_size * cross_indicator)

            status = cross_order.new(orderQty=first_order.cumQty, ordType="Limit", side=cross_side, price=cross_price,
                                     execInst="ParticipateDoNotInitiate")

            if status is None:
                continue

            cross_order.get_status()
            time.sleep(1)

            if cross_order.ordStatus == 'Canceled':
                time.sleep(1)
                continue

            break

        past_qtys = []
        past_prices = [-1,]
        ally_side = first_order.side
        ally_order_properties = []

        counter = 1
        factor = []
        while True:
            factor.extend([counter] * (counter * counter))
            if len(factor) > 100:
                break
            counter += 1

        ally_order_properties = initial_plus1_later_200(10, first_order.price)

        ally_prices, ally_qtys = zip(*ally_order_properties)

        while True:

            # Get status of cross order and break if it is fully filled
            cross_order.get_status()
            if cross_order.ordStatus in ('Filled', 'Canceled'):
                break

            # Choose the order that needs to be placed
            for ally_price, ally_qty in ally_order_properties:

                index = ally_prices.index(ally_price)
                ltp = self.ws.ltp()
                if (ally_side == 'Buy' and ltp < ally_price) or\
                    (ally_side == 'Sell' and ltp > ally_price):
                    continue

                # Get open orders
                open_prices = [-1,]
                open_index = [-1,]
                open_orders = self.ws.open_orders()
                for o in open_orders:
                    if o['side'] == ally_side:
                        open_prices.append(o['price'])
                        open_index.append(ally_prices.index(o['price']))

                # Restrict the number of open ally orders
                if ally_price not in past_prices and ally_price not in open_prices:

                    # If the number of open orders exceeds 2
                    if len(open_orders) > 2:
                        # Break the iteration if the current index is higher than open indexes
                        if index >= max(open_index):
                            break

                        # Cancel the higher index
                        max_price = ally_prices[max(open_index)]
                        for o in open_orders:
                            if o['price'] == max_price:
                                temp = Order(self)
                                temp.orderID = o['orderID']
                                temp.cancel()
                                time.sleep(1)
                                if max_price in past_prices:
                                    past_prices.remove(max_price)
                                    past_qtys.remove(o['orderQty'])
                                break

                        break
                    else:
                        order = Order(self)
                        status = order.new(orderQty=ally_qty, ordType="Limit", side=ally_side,
                                            price=ally_price, execInst="ParticipateDoNotInitiate")

                        if status is None:
                            break
                        else:
                            if order.ordStatus == 'Canceled':
                                time.sleep(1)
                            else:
                                past_prices.append(ally_price)
                                past_qtys.append(ally_qty)
                                break

            # Get open position and amend cross order if necessary
            position = self.ws.get_position()
            if position is not None:
                try:
                    # Get open orders
                    open_prices = [-1, ]
                    open_orders = self.ws.open_orders()
                    for o in open_orders:
                        if o['side'] == ally_side:
                            open_prices.append(o['price'])

                    filled_prices = [p for p in past_prices if p not in open_prices]
                    max_index = 0
                    if len(filled_prices) > 0:
                        if ally_side == 'Buy':
                            max_index = ally_prices.index(min(filled_prices))
                        else:
                            max_index = ally_prices.index(max(filled_prices))
                    increments = (incremental_tick + max_index) * self.tick_size
                    total_cum_qty = abs(position['currentQty'])
                    average_price = position['avgEntryPrice'] + (increments * cross_indicator)
                    average_price = round(self.tick_size * round(average_price / self.tick_size), self.num_decimals)

                    if total_cum_qty != cross_order.orderQty or average_price != cross_order.price:
                        # Amend the cross order
                        cross_order.amend(orderID=cross_order.orderID, orderQty=total_cum_qty, price=average_price)
                        time.sleep(0.5)
                except Exception as e:
                    self.logger.warning(e)

        # Cancel all orders
        self.client.cancel_all()

    def worker_close_depths(self, qty=1):
        while True:
            self.logger.info("Waiting for opportunity")

            side, start_price, ratio = self.opportunity.wait_for_close_depths(depths=1)
            # side, start_price, ratio = 'Buy', self.ws.market_depth()[0]['bids'][0][0], 2

            self.logger.info("Got opportunity")

            first_order = self.make_first_order(side, qty, start_price)
            if first_order.ordStatus == 'Filled':
                break

        market_price = first_order.price
        plus_or_minus = 1 if side == 'Buy' else -1
        gain_price = market_price + ratio * plus_or_minus
        risk_price = market_price + 5 * plus_or_minus * -1
        new_side = 'Sell' if side == 'Buy' else 'Buy'

        gain_order = self.client.new_order(orderQty=qty, ordType="Limit", side=new_side, price=gain_price)
        gain_order['text'] = 'Gain order'
        self.record_order(**gain_order)

        risk_order = self.client.new_order(orderQty=qty, ordType="StopLimit", execInst="LastPrice",
                                           stopPx=risk_price + (2 * plus_or_minus), side=new_side, price=risk_price)
        risk_order['text'] = 'Risk order'
        self.record_order(**risk_order)

        while True:

            for e in self.ws.ws.data['execution']:
                if e['ordStatus'] in ('Canceled', 'Filled'):
                    if e['orderID'] == risk_order['orderID']:
                        risk_order = e
                        gain_order = self.client.cancel_order(orderID=risk_order['orderID'])
                        break
                    elif e['orderID'] == gain_order['orderID']:
                        gain_order = e
                        risk_order = self.client.cancel_order(orderID=risk_order['orderID'])
                        break
            else:
                continue

            break

            # time_diff = datetime.utcnow() - first_order['timestamp'].replace(tzinfo=None)
            # if time_diff.total_seconds() > 600:
            #     ticker = self.ticker()
            #     if ticker is None:
            #         continue
            #
            #     ltp = ticker['last']
            #     if (ltp - first_order['price']) * plus_or_minus >= 0:
            #         continue
            #
            #     risk_order = self.client.cancelOrder(orderID=risk_order['orderID'])
            #     gain_order = self.client.cancelOrder(orderID=gain_order['orderID'])
            #     first_order = self.client.newOrder(orderQty=qty, ordType="Market", side=new_side)
            #     first_order['text'] = 'Risk order'
            #     self.record_order(**first_order)

        self.update_order(**gain_order)
        self.update_order(**risk_order)

    def simulate(self, qty=1):
        self.logger.info("Waiting for opportunity")

        side, start_price, ratio = self.opportunity.wait_for_close_depths()

        self.logger.info("Got opportunity")
        ticker = self.ws.ticker()
        if ticker is None:
            return

        first_order = self.record_order(orderID=uuid.uuid1().hex, ordType="Market", side=side,
                                          price=ticker['last'], timestamp=datetime.utcnow(),
                                          remark="First order", ordStatus="Filled")

        market_price = ticker['last']
        plus_or_minus = 1 if side == 'Buy' else -1
        gain_price = market_price + ratio * plus_or_minus
        risk_price = market_price + 5 * plus_or_minus * -1
        new_side = 'Sell' if side == 'Buy' else 'Buy'

        gain_order = self.record_order(orderID=uuid.uuid1().hex, ordType="MarketIfTouched", side=new_side,
                                       price=gain_price, timestamp=datetime.utcnow(), text="Gain order")
        risk_order = self.record_order(orderID=uuid.uuid1().hex, ordType="StopMarket", side=new_side,
                                       price=risk_price, timestamp=datetime.utcnow(), text="Risk order")

        remark = None
        while remark is None:
            t = self.ws.ticker()
            if t is None:
                continue

            last = t['last']
            if (new_side == 'Buy' and last <= gain_price) or (new_side == 'Sell' and last >= gain_price):
                remark = 'Gain'
            elif (new_side == 'Buy' and last >= risk_price) or (new_side == 'Sell' and last <= risk_price):
                remark = 'Loss'
            else:
                time_diff = datetime.utcnow() - first_order.timestamp
                if time_diff.total_seconds() > 60:
                    if (last - first_order.price) * plus_or_minus < 0:
                        remark = 'Loss'
                        risk_order.price = last
                        risk_order.save()

        if remark is 'Gain':
            gain_order.ordStatus = 'Filled'
            risk_order.ordStatus = 'Canceled'
        else:
            gain_order.ordStatus = 'Canceled'
            risk_order.ordStatus = 'Filled'

        gain_order.timestamp = datetime.utcnow()
        risk_order.timestamp = datetime.utcnow()

        gain_order.save()
        risk_order.save()
