from os import mkdir, path
import logging
import os
import serial
import pynmea2
import datetime
import json

import pyubx2.ubxtypes_core as ubt

from pyubx2.ubxreader import UBXReader
from datetime import datetime


log = logging.getLogger(__name__)


class UbxNmeaReader(UBXReader):

    def __init__(self, stream, *args, **kwargs):
        super().__init__(stream, *args, **kwargs)

    def read(self) -> tuple:
        reading = True
        raw_data = None
        parsed_data = None

        byte1 = self._stream.read(1)  # read the first byte

        while reading:
            is_ubx = False
            is_nmea = False
            if len(byte1) < 1:  # EOF
                break
            if byte1 == b"\xb5":
                byte2 = self._stream.read(1)
                if len(byte2) < 1:  # EOF
                    break
                if byte2 == b"\x62":
                    is_ubx = True
            if is_ubx:  # it's a UBX message
                byten = self._stream.read(4)
                if len(byten) < 4:  # EOF
                    break
                clsid = byten[0:1]
                msgid = byten[1:2]
                lenb = byten[2:4]
                leni = int.from_bytes(lenb, "little", signed=False)
                byten = self._stream.read(leni + 2)
                if len(byten) < leni + 2:  # EOF
                    break
                plb = byten[0:leni]
                cksum = byten[leni: leni + 2]
                raw_data = ubt.UBX_HDR + clsid + msgid + lenb + plb + cksum
                parsed_data = self.parse(
                    raw_data,
                    validate=self._validate,
                    msgmode=self._mode,
                    parsebitfield=self._parsebf,
                )
                reading = False
            else:  # it's not a UBX message (NMEA or something else)
                prevbyte = byte1
                byte1 = self._stream.read(1)
                # "$G" or "$P"
                if prevbyte == b"\x24" and byte1 in (b"\x47", b"\x50"):
                    is_nmea = True  # looks like an NMEA message

                    nmea_rest = self._stream.readline()
                    raw_data = (prevbyte+byte1 +
                                nmea_rest).decode('utf-8').strip()
                    parsed_data = pynmea2.parse(raw_data)
                    reading = False

        return is_nmea, is_ubx, raw_data, parsed_data


class Gnss:
    _serial = None
    REPEATER_INDEX_PATH = "repeater_index.txt"

    def __init__(self, configuration):
        self._serial = serial.Serial(
            configuration["gnss_port"], baudrate=configuration["gnss_baudrate"], timeout=1)
        self._ubx_nmea_reader = UbxNmeaReader(stream=self._serial)
        self.output_name = "init.log"
        self.count_of_fix = 0
        self.fix_count_requested = configuration["nmea_fix_count_requested"]
        self.current_gnss_index = 3  # starting at index 0
        self.start_time = None
        self.configuration_repetion = self.check_repeater_index()

        self.gnss_configuration = {
            "GP": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x01\x21\x00\x31\x10\x00\x22\x00\x31\x10\x00\x24\x00\x31\x10\x00\x25\x00\x31\x10\x00\xEF\xC9',
            "GL" : b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x00\x21\x00\x31\x10\x00\x22\x00\x31\x10\x00\x24\x00\x31\x10\x00\x25\x00\x31\x10\x01\xEF\xB5',
            "GA": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x00\x21\x00\x31\x10\x01\x22\x00\x31\x10\x00\x24\x00\x31\x10\x00\x25\x00\x31\x10\x00\xEF\xC4',
            "GPGL": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x01\x21\x00\x31\x10\x01\x22\x00\x31\x10\x00\x24\x00\x31\x10\x00\x25\x00\x31\x10\x00\xF0\xD9',
            "GPGA": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x01\x21\x00\x31\x10\x01\x22\x00\x31\x10\x00\x24\x00\x31\x10\x00\x25\x00\x31\x10\x00\xF0\xD9',
            "GAGL": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x00\x21\x00\x31\x10\x01\x22\x00\x31\x10\x00\x24\x00\x31\x10\x00\x25\x00\x31\x10\x01\xF0\xC5',
            "GPGLGA": b'\xB5\x62\x06\x8A\x4F\x00\x01\x01\x00\x00\x01\x00\x31\x10\x01\x03\x00\x31\x10\x01\x07\x00\x31\x10\x01\x0A\x00\x31\x10\x01\x0D\x00\x31\x10\x01\x0E\x00\x31\x10\x01\x12\x00\x31\x10\x01\x15\x00\x31\x10\x01\x18\x00\x31\x10\x01\x1A\x00\x31\x10\x01\x1F\x00\x31\x10\x01\x21\x00\x31\x10\x01\x22\x00\x31\x10\x00\x24\x00\x31\x10\x00\x25\x00\x31\x10\x01\xF1\xDA',
        }

        self.log_dir = self.make_log_dir()
        self.change_configuration()

    def run(self):

        last_data_get = datetime.utcnow()
        while self._serial.isOpen():
            # reboot without any new data in 1800 = 30 min
            if (datetime.utcnow() - last_data_get).total_seconds() <= 1800:

                if self._serial.in_waiting:

                    try:

                        is_nmea, is_ubx, raw_data, parsed_data = self._ubx_nmea_reader.read()

                        if is_nmea:
                            last_data_get = datetime.utcnow()
                            self.write_nmea_data(
                                str(last_data_get)+"::"+raw_data)
                            # check gga condition for gga
                            if isinstance(parsed_data, pynmea2.types.talker.GGA):
                                self.check_gga(parsed_data)

                        if is_ubx:
                            last_data_get = datetime.utcnow()
                            self.write_ubx_data(raw_data)

                    except Exception as e:
                        log.exception(e)
            else:
                log.debug("GNSS reading is freezed, restarting system")
                os.system("sudo reboot")

        log.info("Gnss stopped")

    def check_gga(self, gga):

        # calculate difference
        time_diff = (datetime.utcnow() - self.start_time)

        if gga.gps_qual == 4:
            self.count_of_fix += 1

            if self.count_of_fix == 1:
                self.write_timer_log("first RTK_Fix")
            elif self.count_of_fix == self.fix_count_requested:
                self.write_timer_log(
                    "required number {} reached".format(self.fix_count_requested))
                self.change_configuration()
            elif time_diff.total_seconds() > 900:  # 900 seconds = 15 mins
                self.write_timer_log(
                    "In 900s reached only {} fix -> changing config".format(self.fix_count_requested))
                self.change_configuration()

    def check_repeater_index(self) -> int:

        index = 0
        try:
            if os.path.exists(self.REPEATER_INDEX_PATH):

                with open(self.REPEATER_INDEX_PATH, "r") as file:
                    line = file.readline()
                    index = int(line)
                    log.debug("Actual index {}".format(index))
                    return index

            else:
                return index
        except Exception as err:
            log.exception("Some error in check rep. index::\n"+err)
            return index

    def write_repeater_index(self) -> None:

        try:

            with open(self.REPEATER_INDEX_PATH, "w") as file:
                file.write(str(self.configuration_repetion))

        except Exception as err:
            log.exception("Some error in writing rep. index::\n"+err)

    def change_configuration(self):

        config_keys = list(self.gnss_configuration.keys())

        self.current_gnss_index += 1

        if self.current_gnss_index >= len(config_keys):
            self.current_gnss_index = 1
            self.configuration_repetion += 1
            self.write_repeater_index()

        self.count_of_fix = 0
        self._serial.write(
            self.gnss_configuration[config_keys[self.current_gnss_index]])
        self.set_gnss_cold_start()
        self.start_time = datetime.utcnow()

        # flush all data in buffer
        try:
            self._serial.read_all()
        except Exception as e:
            log.exception("Flush serial data error: {}".format(e))

        self.set_output_filenames(
            config_keys[self.current_gnss_index], self.configuration_repetion)
        self.write_timer_log("start {} configuration".format(
            config_keys[self.current_gnss_index]))

    def set_gnss_cold_start(self) -> None:
        self._serial.write(b'\xB5\x62\x06\x04\x04\x00\xFF\xB9\x02\x00\xC8\x8F')

    def get_count_of_fix(self) -> int:
        return self.count_of_fix

    def make_log_dir(self) -> str:
        log_dir_path = datetime.utcnow().strftime("%H_%M_00__%d_%m_%Y")
        if not os.path.exists(log_dir_path):
            mkdir(log_dir_path)
        return log_dir_path

    def set_output_filenames(self, gnss_type: str, count: int) -> None:
        self.output_name = os.path.join(
            self.log_dir, "{}_{}".format(gnss_type, count))

    def write_nmea_data(self, data: str = "") -> None:
        with open(self.output_name+"_nmea.log", "a") as file:
            file.write(data+"\n")

    def write_ubx_data(self, data: bytearray) -> None:
        with open(self.output_name+"_ubx.log", "ab") as file:
            file.write(data)

    def write_timer_log(self, desc="start"):
        time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        with open(self.output_name+"_time.log", "a") as file:
            file.write("{}:: {}\n".format(time, desc))

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
