import uuid
import logging
import time
from bm.lib.user import User
from bm.lib.rest import RestClient

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

    def do(self):

        data = {}
        with open('keys.txt', 'r') as f:
            for line in f.readlines():
                k, v = line.split('=')
                data[k.strip()] = v.strip()

        symbol = data.get('symbol', 'XBTUSD')
        endpoint = data.get('endpoint', "https://testnet.bitmex.com/api/v1")

        user = User(data['key'], data['secret'], symbol, endpoint, dry_run=True)

        count = 0
        while count < 500:
            count += 1
            logging.info('Iteration starting: {}'.format(count))
            user.parent_order = ParentOrder.objects.create(uid=uuid.uuid1(), name='Close_depths')
            user.worker_incremental_order(10)
            logging.info('Iteration completed: {}'.format(count))
            self.log_summary()
            time.sleep(5)
            break
