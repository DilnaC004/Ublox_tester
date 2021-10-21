import socket
import serial
import base64
import json
import os
import logging

from serial.serialwin32 import Serial

log = logging.getLogger(__name__)


class Ntrip:
    def __init__(self, config: dict, port: serial.Serial) -> None:
        self._ntrip_server = config["ntrip_server"]
        self._ntrip_port = config["ntrip_port"]
        self._ntrip_mountpoint = config["ntrip_mountpoint"]
        self._ntrip_user = config["ntrip_user"]
        self._ntrip_password = config["ntrip_password"]
        self._ntrip_access = self.get_access_string()
        self._serial_port = port

        log.info('NTRIP imported')

    def run(self):

        while True:
            try:
                self.connect_server()
            except Exception as er:
                logging.exception(er)

    def connect_server(self):

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self._ntrip_server, self._ntrip_port))
            s.sendall(self.get_server_connection_string())

            while True:
                received_data = s.recv(1024)

                if not received_data:
                    print("breaking")
                    break

                print(received_data)

                # check serial for debug output
                if type(self._serial_port) == serial.Serial:
                    self._serial_port.write(received_data)
                else:
                    print(received_data)

    def get_access_string(self):
        auth = "{}:{}".format(
            self._ntrip_user, self._ntrip_password).encode("utf-8")
        return base64.b64encode(auth).decode("utf-8")

    def get_server_connection_string(self):

        return ("GET /{} HTTP/1.0\r\n"
                "Host:{}\r\n"
                "User-Agent: NTRIPClient for pythonScript\r\n"
                "Authorization: Basic {}\r\n\r\n").format(self._ntrip_mountpoint, self._ntrip_server, self._ntrip_access).encode("utf-8")


if __name__ == "__main__":

    """Testing NTRIP function"""

    config_path = "configuration.json"

    if not os.path.exists(config_path):
        logging.exception(
            'Configuration file "{}" doesnt exist.'.format(config_path))

    with open(config_path) as file:
        conf = json.load(file)

    ntrip = Ntrip(conf, None)
    ntrip.run()
