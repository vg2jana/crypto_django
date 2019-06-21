import time
import statistics
from datetime import datetime, timedelta


class StabilityTimer:

    def __init__(self, max_counter):
        self.counter = 1
        self.side = None
        self.max_counter = max_counter

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


class Opportunity:

    def __init__(self, websocket, client):
        self.ws = websocket
        self.client = client

    def bid_ask_size(self):
        depth = None
        while depth is None:
            depth = self.ws.depth_info()

        mid_price = self.ws.ticker()['mid']
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

    def wait_for_close_depths(self, depths=3):

        side = None
        min_first_depth = 400000
        max_first_depth = 600000
        cross_max_vol = 100000
        ratio = 2
        price = -1

        while side is None:
            depth = self.ws.market_depth()
            if depth is None:
                continue

            bids = [x for x in depth[0]['bids'][:depths]]
            asks = [x for x in depth[0]['asks'][:depths]]
            bid_prices, bid_volumes = list(zip(*bids))
            ask_prices, ask_volumes = list(zip(*asks))

            total_bid_volume = sum(bid_volumes)
            total_ask_volume = sum(ask_volumes)

            if bid_volumes[0] > min_first_depth and bid_volumes[0] < max_first_depth and total_ask_volume < cross_max_vol:
                side = 'Buy'
                price = bid_prices[0]
                # if min(bid_volumes[1], bid_volumes[2]) > 500000:
                #     ratio = 5

            if ask_volumes[0] > min_first_depth and ask_volumes[0] < max_first_depth and total_bid_volume < cross_max_vol:
                side = 'Sell'
                price = ask_prices[0]
                # if min(ask_volumes[1], ask_volumes[2]) > 500000:
                #     ratio = 5

        return side, price, 2

    def wait_for_high_volume(self, min_volume, trigger_ratio):
        stability_timer = StabilityTimer(3)

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

    def buy_or_sell(self):

        side = None
        while side is None:
            past_12h_bucket = None
            while past_12h_bucket is None:
                past_12h = datetime.utcnow() - timedelta(hours=12)
                past_12h_bucket = self.client.trade_bucket(binSize="1h", startTime=past_12h)

            tide = []
            for bucket in past_12h_bucket:
                tide.extend((bucket['high'], bucket['low']))

            low = min(tide)
            high = max(tide)
            mean = (high - low) / 2

            ltp = self.ws.ltp()
            stddev = statistics.pstdev(tide)

            if ltp <= (mean - stddev) or ltp >= (mean + stddev):
                time.sleep(5)
                continue

            funding_rate = self.client.funding_rate()
            if funding_rate is not None:
                if funding_rate >= 0:
                    side = 'Buy'
                else:
                    side = 'Sell'

        return side
