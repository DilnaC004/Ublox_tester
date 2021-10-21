import json
import pathlib

from gnss import Gnss
from ntrip import Ntrip


class GNSStester:

    def __init__(self, config_file_path) -> None:
        pass


if __name__ == "__main__":
    config_path = "configuratiion.json"
    if not pathlib.Path(config_path).exists():
        raise Exception(
            'Configuration file "{}" doesnt exist.'.format(config_path))

    tester = GNSStester(config_path)
