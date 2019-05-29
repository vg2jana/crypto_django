import time
import uuid
import sys
import websocket
import logging

from datetime import datetime
from bitmex_websocket import BitMEXWebsocket
from bm.models import ParentOrder, Order


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

    def __init__(self, name, key, secret, symbol, endpoint, dry_run=True):

        self.logger = logging.getLogger()
        self.order_attrs = [f.name for f in Order._meta.get_fields()]
        self.endpoint = endpoint
        self.key = key
        self.secret = secret
        self.symbol = symbol
        self.ws = None
        self.dry_run = dry_run
        self.parent_order = ParentOrder.objects.create(uid=uuid.uuid1(), name=name)

    def connect_ws(self):
        while True:
            self.logger.info('Attempting to connect WS')
            try:
                self.ws = BitMEXWebsocket(endpoint=self.endpoint, symbol=self.symbol,
                                          api_key=self.key, api_secret=self.secret)
                self.ws.get_instrument()
                break
            except Exception as e:
                self.logger.warning(e)
            time.sleep(1)
        self.logger.info('Connected to WS')

    def try_ping(self):
        if self.ws.ws.sock is None:
            self.connect_ws()

        try:
            self.ws.ws.sock.ping()
        except websocket.WebSocketConnectionClosedException as e:
            self.logger.warning(e)
            self.connect_ws()
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
        level_up = mid_price + mid_price * 0.001
        level_down = mid_price - mid_price * 0.001

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

        kwargs["symbol"] = self.client.symbol
        kwargs["ordStatus"] = kwargs.get("ordStatus", "New")
        kwargs["parentOrder"] = self.parent_order
        kwargs = {k: v for k, v in kwargs.items() if k in self.order_attrs}
        order = Order.objects.create(**kwargs)
        self.logger.info("NEW Type: {}, Text: {}, Status: {}, Side: {}, Price: {}", order.ordType, order.text,
                         order.ordStatus, order.side, order.price)
        return order

    def update_order(self, **kwargs):

        self.logger.info(kwargs)
        order_id = kwargs.pop('orderID')
        self.client.getOrder(orderID=order_id)

        order = Order.objects.filter(orderID__exact=order_id).first()
        for k, v in kwargs.items():
            order.__setattr__(k, v)

        self.logger.info("UPDATE Type: {}, Text: {}, Status: {}, Side: {}, Price: {}", order.ordType, order.text,
                         order.ordStatus, order.side, order.price)
        order.save()

    def wait_for_close_depths(self, depths=3):

        side = None
        min_first_depth = 1200000
        cross_max_vol = 100000

        while side is None:
            depth = self.ws.market_depth()
            if depth is None:
                continue

            bids = [x[1] for x in depth[0]['bids'][:depths]]
            asks = [x[1] for x in depth[0]['asks'][:depths]]

            sum_bids = sum(bids)
            sum_asks = sum(asks)

            if bids[0] > min_first_depth and sum_asks < cross_max_vol:
                side = 'Buy'

            if asks[0] > min_first_depth and sum_bids < cross_max_vol:
                side = 'Sell'

        return side, 1

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

    def worker(self, qty=1, min_volume=7000000, trigger_ratio=5, price_multiplier=4):

        self.logger.info("Waiting for opportunity")
        # side, ratio = self.wait_for_opportunity(min_volume, trigger_ratio)
        side, ratio = self.wait_for_close_depths()

        if self.dry_run is False:
            self.logger.info("Got opportunity")
            market_order = self.client.newOrder(orderQty=qty, ordType="Market", side=side)
            market_order['text'] = 'First order'
            self.record_order(**market_order)

            market_price = market_order['price']
            plus_or_minus = 1 if side == 'Buy' else -1
            gain_price = market_price + ratio * price_multiplier * plus_or_minus
            risk_price = market_price + 10 * plus_or_minus * -1
            new_side = 'Sell' if side == 'Buy' else 'Buy'

            gain_order = self.client.newOrder(orderQty=qty, ordType="MarketIfTouched", execInst="LastPrice",
                                               stopPx=gain_price, side=new_side)
            gain_order['text'] = 'Gain order'
            self.record_order(**gain_order)

            risk_order = self.client.newOrder(orderQty=qty, ordType="StopMarket", execInst="LastPrice",
                                               stopPx=risk_price, side=new_side)
            risk_order['text'] = 'Risk order'
            self.record_order(**risk_order)

            while True:

                orders = self.client.openOrders()
                if orders is None:
                    continue

                order_ids = [o['orderID'] for o in orders]

                if gain_order['orderID'] not in order_ids:
                    risk_order = self.client.cancelOrder(orderID=risk_order['orderID'])
                    break
                elif risk_order['orderID'] not in order_ids:
                    gain_order = self.client.cancelOrder(orderID=gain_order['orderID'])
                    break

                time_diff = datetime.utcnow() - market_order.timestamp
                if time_diff.total_seconds() > 60:
                    ticker = self.ticker()
                    if ticker is None:
                        continue

                    ltp = ticker['last']
                    if (ltp - market_order['price']) * plus_or_minus >= 0:
                        continue

                    risk_order = self.client.cancelOrder(orderID=risk_order['orderID'])
                    gain_order = self.client.cancelOrder(orderID=gain_order['orderID'])
                    market_order = self.client.newOrder(orderQty=qty, ordType="Market", side=new_side)
                    market_order['text'] = 'Risk order'
                    self.record_order(**market_order)

            self.update_order(**gain_order)
            self.update_order(**risk_order)

        else:
            ticker = self.ticker()
            if ticker is None:
                return

            market_order = self.record_order(orderID=uuid.uuid1().hex, ordType="Market", side=side,
                                              price=ticker['last'], timestamp=datetime.utcnow(),
                                              remark="First order", ordStatus="Filled")

            market_price = ticker['last']
            plus_or_minus = 1 if side == 'Buy' else -1
            gain_price = market_price + ratio * price_multiplier * plus_or_minus
            risk_price = market_price + 5 * plus_or_minus * -1
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
                else:
                    time_diff = datetime.utcnow() - market_order.timestamp
                    if time_diff.total_seconds() > 60:
                        if (last - market_order.price) * plus_or_minus < 0:
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
