import time
import uuid
import sys
import websocket
import logging

from datetime import datetime
from bitmex_websocket import BitMEXWebsocket
from bm.models import Order

from bm.lib.client import RestClient


class StabilityTimer:

    def __init__(self):
        self.counter = 1
        self.side = None

    def reset(self):
        self.counter = 1

    def increment(self):
        self.counter += 1

    def update(self, side):
        if self.side is None or side == self.side:
            self.increment()
        else:
            self.reset()

        self.side = side

    def trigger(self):
        if self.counter > 3:
            return True

        return False


class User:

    def __init__(self, name, key, secret, symbol, endpoint):
        try:
            self.client = RestClient(key, secret, symbol)
            self.ws = BitMEXWebsocket(endpoint=endpoint, symbol=symbol, api_key=key, api_secret=secret)
        except Exception as e:
            print(e)
            sys.exit(1)
        self.ws.get_instrument()
        self.order_attrs = [f.name for f in Order._meta.get_fields()]
        self.name = name
        self.endpoint = endpoint
        self.key = key
        self.secret = secret
        self.symbol = symbol
        self.logger = logging.getLogger()

    def try_ping(self):
        try:
            self.ws.ws.send('ping')
        except websocket.WebSocketConnectionClosedException as e:
            self.ws = BitMEXWebsocket(endpoint=self.endpoint, symbol=self.symbol,
                                      api_key=self.key, api_secret=self.secret)
        except Exception as e:
            self.logger.warning(e)

    def depth_info(self):
        self.try_ping()
        try:
            return self.ws.market_depth()
        except Exception as e:
            self.logger.warning("Error fetching market depth")
            self.logger.warning(e)

        return None

    def ticker(self):
        self.try_ping()
        try:
            return self.ws.get_ticker()
        except Exception as e:
            self.logger.warning("Error fetching ticker")
            self.logger.warning(e)

        return None

    def open_orders(self):
        self.try_ping()
        try:
            return self.ws.open_orders('')
        except Exception as e:
            self.logger.warning("Error fetching Open orders")
            self.logger.warning(e)

        return None

    def bid_ask_size(self):
        depth = None
        while depth is None:
            depth = self.depth_info()

        mid_price = self.ticker()['mid']
        level_up = mid_price + mid_price * 0.003
        level_down = mid_price - mid_price * 0.003

        bids = 0
        asks = 0
        for d in depth:
            side = d['side']
            price = d['price']
            size = d['size']
            if side == 'Buy':
                if price < level_down:
                    continue
                bids += size
            else:
                if price > level_up:
                    continue
                asks += size

            if price < level_down and price > level_up:
                break

        return (bids, asks)

    def record_order(self, **kwargs):

        kwargs["name"] = self.name
        kwargs["symbol"] = self.client.symbol
        kwargs["ordStatus"] = kwargs.get("ordStatus", "New")
        kwargs = {k: v for k, v in kwargs.items() if k in self.order_attrs}
        self.logger.info(kwargs)
        return Order.objects.create(**kwargs)

    def update_order(self, **kwargs):

        self.logger.info(kwargs)
        order_id = kwargs.pop('orderID')
        self.client.getOrder(orderID=order_id)

        order = Order.objects.filter(orderID__exact=order_id).first()
        for k, v in kwargs.items():
            order.__setattr__(k, v)

        order.save()

    def wait_for_opportunity(self, min_volume, trigger_ratio):
        stability_timer = StabilityTimer()

        while True:
            time.sleep(stability_timer.counter)
            (bids, asks) = self.bid_ask_size()

            if bids == 0 or asks == 0:
                stability_timer.reset()
                continue

            if bids > asks:
                ratio = int(bids / asks)
                side = "Buy"
            else:
                ratio = int(asks / bids)
                side = "Sell"

            if max(bids, asks) < min_volume:
                stability_timer.reset()
                continue

            if ratio < trigger_ratio:
                stability_timer.reset()
                continue

            stability_timer.update(side)
            if stability_timer.trigger() is False:
                continue

            break

        ratio = min(ratio, 5)
        return side, ratio

    def worker(self, qty=1, min_volume=7000000, trigger_ratio=5, price_multiplier=1.5, dry_run=False):

        side, ratio = self.wait_for_opportunity(min_volume, trigger_ratio)

        if dry_run is False:
            market_order = self.client.newOrder(orderQty=qty, ordType="Market", side=side)
            self.record_order(**market_order)

            market_price = market_order['price']
            plus_or_minus = 1 if side == 'Buy' else -1
            gain_price = market_price + ratio * price_multiplier * plus_or_minus
            risk_price = market_price + 50 * plus_or_minus * -1
            new_side = 'Sell' if side == 'Buy' else 'Buy'

            gain_order = self.client.newOrder(orderQty=qty, ordType="MarketIfTouched", execInst="LastPrice",
                                               stopPx=gain_price, side=new_side)
            self.record_order(**gain_order)

            risk_order = self.client.newOrder(orderQty=qty, ordType="StopMarket", execInst="LastPrice",
                                               stopPx=risk_price, side=new_side)
            self.record_order(**risk_order)

            while True:

                time.sleep(5)
                orders = self.client.openOrders()
                if orders is None:
                    continue

                order_ids = [o['orderID'] for o in orders]

                if gain_order['orderID'] not in order_ids:
                    self.client.cancelOrder(orderID=risk_order['orderID'])
                    break
                elif risk_order['orderID'] not in order_ids:
                    self.client.cancelOrder(orderID=gain_order['orderID'])
                    break

            self.update_order(**gain_order)
            self.update_order(**risk_order)

        else:
            ticker = self.ticker()
            if ticker is None:
                return

            self.record_order(orderID=uuid.uuid1().hex, ordType="Market", side=side,
                              price=ticker['last'], timestamp=datetime.utcnow(),
                              remark="First order", ordStatus="Filled")

            market_price = ticker['last']
            plus_or_minus = 1 if side == 'Buy' else -1
            gain_price = market_price + ratio * price_multiplier * plus_or_minus
            risk_price = market_price + 50 * plus_or_minus * -1
            new_side = 'Sell' if side == 'Buy' else 'Buy'

            gain_order = self.record_order(orderID=uuid.uuid1().hex, ordType="MarketIfTouched", side=new_side,
                                           price=gain_price, timestamp=datetime.utcnow(), text="Gain order")
            risk_order = self.record_order(orderID=uuid.uuid1().hex, ordType="StopMarket", side=new_side,
                                           price=risk_price, timestamp=datetime.utcnow(), text="Risk order")

            remark = None
            while remark is None:
                t = self.ticker()
                if t is None:
                    continue

                last = t['last']
                if (new_side == 'Buy' and last <= gain_price) or (new_side == 'Sell' and last >= gain_price):
                    remark = 'Gain'
                elif (new_side == 'Buy' and last >= risk_price) or (new_side == 'Sell' and last <= risk_price):
                    remark = 'Loss'

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
