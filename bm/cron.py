import uuid
import logging
import time
import sys
import os
import json
from bm.lib.user import User
from bm.lib.order import Order

# from django.conf import settings
# settings.configure()
# python3 manage.py runcrons --force
# python3 manage.py runcrons "bm.cron.SampleCronJob"
from django_cron import CronJobBase, Schedule
from bm.models import ParentOrder

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, filemode='a', filename='app.log')


class SampleCronJob(CronJobBase):
    RUN_EVERY_MINS = 1440 # every 24 hours

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'bm.sampleCron'

    def log_summary(self):

        gain = 0
        loss = 0
        for p in ParentOrder.objects.all():
            m = None
            g = None
            l = None
            # diff = 0
            for o in p.order_set.all():
                if o.ordType == 'Market':
                    m = o
                elif o.text == 'Gain order' and o.ordStatus == 'Filled':
                    g = o
                elif o.text == 'Risk order' and o.ordStatus == 'Filled':
                    l = o
            if g is not None:
                # diff = (g.timestamp - m.timestamp)
                gain += abs(m.price - g.price)
            if l is not None:
                # diff = (l.timestamp - m.timestamp)
                loss += abs(m.price - l.price)
            # if diff != 0:
            #     print(diff.total_seconds())

        logging.info("SUMMARY:\nTotal iterations: {}\nGain: {}\nLoss: {}\nNet: {}\n".format(ParentOrder.objects.count(),
                                                                                            gain, loss, gain - loss))

    def generate_open_order(self, user):
        open_order = None
        position = user.ws.get_position()
        if position is not None:
            open_order = Order(user)
            open_order.orderQty = position['currentQty']
            open_order.cumQty = abs(position['currentQty'])
            open_order.price = round(user.tick_size * round(position['avgEntryPrice'] / user.tick_size),
                                     user.num_decimals)
            if position['currentQty'] > 0:
                open_order.side = 'Buy'
            else:
                open_order.side = 'Sell'

        return open_order

    def do(self):

        logging.info("My PID: {}".format(os.getpid()))

        data = {}
        with open('keys.txt', 'r') as f:
            for line in f.readlines():
                k, v = line.split('=')
                data[k.strip()] = v.strip()

        symbol = data.get('symbol', 'XBTUSD')

        dry_run = False
        if dry_run is True:
            endpoint = data.get('endpoint', "https://testnet.bitmex.com/api/v1")
        else:
            endpoint = data.get('endpoint', "https://www.bitmex.com/api/v1")

        user = User(data['key'], data['secret'], symbol, endpoint, dry_run=dry_run)

        count = 0
        open_order = None
        while True or open_order is not None:
            # Choose side and qty
            ltp_range = data['side']
            qty = int(data['qty'])
            step = int(data['step'])
            side = user.opportunity.buy_sell_range(json.loads(ltp_range))

            # Cancel all open orders
            user.client.cancel_all()
            time.sleep(5)

            count += 1
            logging.info('Iteration starting: {}'.format(count))
            user.parent_order = ParentOrder.objects.create(uid=uuid.uuid1(), name='Incremental quantity')

            open_order = self.generate_open_order(user)

            # See if price is in better gain
            if open_order is not None:
                if open_order.side == 'Buy':
                    cross_indicator = 1
                    side = 'Sell'
                else:
                    cross_indicator = -1
                    side = 'Buy'
                limit_price = open_order.price + (int(open_order.cumQty / 5) * cross_indicator)
                user.move_and_fill(side, open_order.cumQty, limit_price)

            open_order = self.generate_open_order(user)
            user.worker_incremental_order(qty, side, first_order=open_order, step=step)

            logging.info('Iteration completed: {}'.format(count))
            # self.log_summary()

            # Clear execution data
            user.ws.clear_executions()

            # Restart websocket connection
            user.ws.restart()

            # Verify open order
            open_order = self.generate_open_order(user)

            if open_order is None:
                try:
                    with open('sign.txt', 'r') as f:
                        x = f.read()
                        if 'STOP' in x:
                            logging.info('STOPPING on signal')
                            os.remove('sign.txt')
                            sys.exit(0)
                except Exception as e:
                    pass
