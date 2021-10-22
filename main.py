import json
import os
import logging
import threading

from gnss import Gnss
from ntrip import Ntrip


log_formatter = '%(asctime)s %(name)s %(message)s'

logging.basicConfig(filename="ublox_tester.log",
                    format=log_formatter, level=logging.INFO)
log = logging.getLogger(__name__)


for logger_name in [__name__, "gnss"]:
    logging.getLogger(logger_name).setLevel(logging.INFO)


if __name__ == "__main__":

    config_path = "configuration.json"

    if not os.path.exists(config_path):
        log.exception(
            'Configuration file "{}" doesnt exist.'.format(config_path))

    with open(config_path) as file:
        conf = json.load(file)

    gnss = Gnss(conf)
    ntrip = Ntrip(conf, gnss.get_serial())

    th1 = threading.Thread(target=gnss.run)
    th2 = threading.Thread(target=ntrip.run)

    log.debug("start thread1")
    th1.start()
    log.debug("start thread2")
    th2.start()
