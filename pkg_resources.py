class DistributionNotFound(Exception):
    pass


class Distribution:
    def __init__(self, version):
        self.version = version


def get_distribution(name):
    return Distribution("0.0")
