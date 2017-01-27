from enum import Enum


class Subtype(Enum):
    BASIC = 0,
    YES_NO = 1,
    LOGIN_INFO = 2,
    RECEIVE_FILTER = 3,
    BROADCAST_FILTER = 4


class ConfigType:
    def __init__(self, subtype, multi_value=False, required=False, default=None):
        self._subtype = subtype
        self._multi_value = multi_value
        self._required = required
        self._default = default

    @property
    def subtype(self):
        return self._subtype

    @property
    def multi_value(self):
        return self._multi_value

    @property
    def required(self):
        return self._required

    @property
    def default(self):
        return self._default
