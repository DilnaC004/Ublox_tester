from os import mkdir, path
import logging
import os
import serial
import pynmea2
import datetime
import json

from serial.serialwin32 import Serial

log = logging.getLogger(__name__)


class Gnss:
    _serial = None

    def __init__(self, configuration):
        self._serial = serial.Serial(
            configuration["gnss_port"], baudrate=configuration["gnss_baudrate"], timeout=1)
        self.output_name = "init.log"
        self.count_of_fix = 0
        self.fix_count_requested = configuration["nmea_fix_count_requested"]
        self.current_gnss_index = -1  # starting at index 0
        self.configuration_repetion = 0

        self.gnss_configuration = {
            "GP": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x01\x21\x00\x31\x10\x00\x22\x00\x31\x10\x00\x24\x00\x31\x10\x00\x25\x00\x31\x10\x00\xEF\xC9',
            "GL": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x00\x21\x00\x31\x10\x00\x22\x00\x31\x10\x01\x24\x00\x31\x10\x01\x25\x00\x31\x10\x01\xF1\xC6',
            "GA": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x00\x21\x00\x31\x10\x01\x22\x00\x31\x10\x01\x24\x00\x31\x10\x01\x25\x00\x31\x10\x00\xF1\xD5',
            "GPGL": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x01\x21\x00\x31\x10\x00\x22\x00\x31\x10\x01\x24\x00\x31\x10\x01\x25\x00\x31\x10\x01\xF2\xDB',
            "GPGA": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x01\x21\x00\x31\x10\x01\x22\x00\x31\x10\x01\x24\x00\x31\x10\x01\x25\x00\x31\x10\x00\xF2\xEA',
            "GPGLGA": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x01\x21\x00\x31\x10\x01\x22\x00\x31\x10\x01\x24\x00\x31\x10\x01\x25\x00\x31\x10\x00\xF2\xEA',
        }

        self.log_dir = self.make_log_dir()
        self.change_configuration(
            self.configuration_repetion, self.configuration_repetion)

    def run(self):

        while self._serial.isOpen():

            try:

                # kontrala splnění podmínek

                data = self._serial.readline().decode('utf-8').strip()

                if data[3:6] == "GGA":
                    self.check_gga(data)
                # zapis dat do logu

                self.write_data(data)

            except Exception as e:
                log.exception(e)

        log.info("Gnss stopped")

    def check_gga(self, nmea_str):
        msg = pynmea2.parse(nmea_str)

        if msg.gps_qual == 4:
            self.count_of_fix += 1

            if self.count_of_fix == 1:
                self.write_timer_log("first RTK_Fix")
            elif self.count_of_fix == self.fix_count_requested:
                self.write_timer_log(
                    "required number {} reached".format(self.fix_count_requested))

    def change_configuration(self, gnss_type_index, count_repetion):

        config_keys = list(self.gnss_configuration.keys())

        self.current_gnss_index += 1

        if self.current_gnss_index >= len(config_keys):
            self.current_gnss_index = 1
            self.configuration_repetion += 1

        self.count_of_fix = 0
        self._serial.write(
            self.gnss_configuration[config_keys[self.current_gnss_index]])
        self.set_output_filenames(
            config_keys[self.current_gnss_index], self.configuration_repetion)
        self.write_timer_log("start {} configuration".format(
            config_keys[self.current_gnss_index]))

    def get_count_of_fix(self) -> int:
        return self.count_of_fix

    def make_log_dir(self) -> str:
        log_dir_path = datetime.datetime.now().strftime("%H_%M_00__%d_%m_%Y")
        if not os.path.exists(log_dir_path):
            mkdir(log_dir_path)
        return log_dir_path

    def set_output_filenames(self, gnss_type: str, count: int) -> None:
        self.output_name = os.path.join(
            self.log_dir, "{}_{}".format(gnss_type, count))

    def write_data(self, data: str) -> None:
        with open(self.output_name+".log", "a") as file:
            file.write(data+"\n")

    def write_timer_log(self, desc="start"):
        time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        with open(self.output_name+"_time.log", "a") as file:
            file.write("{}: {}".format(time, desc))

    def get_serial(self) -> serial.Serial:
        return self._serial

    def close_serial(self):
        self._serial.close()


if __name__ == "__main__":
    config_path = "configuration.json"

    if not os.path.exists(config_path):
        logging.exception(
            'Configuration file "{}" doesnt exist.'.format(config_path))

    with open(config_path) as file:
        conf = json.load(file)

    gnss = Gnss(conf)

    gnss.run()
