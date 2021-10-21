from __future__ import with_statement
import socket
from time import time
import serial
import base64
import json
import time
from multiprocessing import Process


class Ntrip:
    def __init__(self, config: dict, port: serial.Serial) -> None:
        self._ntrip_server = config["ntrip_server"]
        self._ntrip_port = config["ntrip_port"]
        self._ntrip_mountpoint = config["ntrip_mountpoint"]
        self._ntrip_user = config["ntrip_user"]
        self._ntrip_password = config["ntrip_password"]
        self._ntrip_access = self.get_access_string()
        self._serial_port = port

    def start(self):

        proc = Process(target=self.connect_server())
        proc.start()

    def connect_server(self):

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self._ntrip_server, self._ntrip_port))
            s.sendall(self.get_server_connection_string())

            while True:
                received_data = s.recv(1024)

                if not received_data:
                    print("breaking")
                    print(received_data)
                    break
                print(received_data)
                # self._serial_port.write(received_data)

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

    conf = {"gnss_port": "",
            "gnss_baudrate": 38400,
            "ntrip_server": "195.245.209.181",
            "ntrip_port": 2101,
            "ntrip_mountpoint": "CPRG3-MSM",
            "ntrip_user": "****",
            "ntrip_password": "*****"}
    print(conf)
    #serr = serial.Serial('COM6', baudrate=38400, timeout=1)
    ntrip = Ntrip(conf, [])

    ntrip.start()

    while True:
        print("HELLO")
        time.sleep(1)
