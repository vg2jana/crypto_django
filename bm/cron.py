import time
import logging
from bm.lib.user import User

# from django.conf import settings
# settings.configure()
# python3 manage.py runcrons --force
# python3 manage.py runcrons "bm.cron.SampleCronJob"
from django_cron import CronJobBase, Schedule

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, filemode='a', filename='app.log')

class SampleCronJob(CronJobBase):
    RUN_EVERY_MINS = 1440 # every 24 hours

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'bm.sampleCron'

    def do(self):

        data = {}
        with open('keys.txt', 'r') as f:
            for line in f.readlines():
                k, v = line.split('=')
                data[k.strip()] = v.strip()

        symbol = data.get('symbol', 'XBTUSD')
        endpoint = data.get('endpoint', "https://www.bitmex.com/api/v1")

        count = 0

        while count < 500:
            count += 1
            logging.info('Iteration starting: {}'.format(count))
            user = User('vol_8M_trratio_2.5', data['key'], data['secret'], symbol, endpoint)
            user.worker(min_volume=8000000, trigger_ratio=2.5, dry_run=True)
            time.sleep(60)
            logging.info('Iteration completed: {}'.format(count))
