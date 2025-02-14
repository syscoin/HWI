# Automatically generated by pb2py
# fmt: off
from .. import protobuf as p

if __debug__:
    try:
        from typing import List
    except ImportError:
        List = None  # type: ignore


class SignMessage(p.MessageType):
    MESSAGE_WIRE_TYPE = 38

    def __init__(
        self,
        address_n: List[int] = None,
        message: bytes = None,
        coin_name: str = None,
        script_type: int = None,
    ) -> None:
        self.address_n = address_n if address_n is not None else []
        self.message = message
        self.coin_name = coin_name
        self.script_type = script_type

    @classmethod
    def get_fields(cls):
        return {
            1: ('address_n', p.UVarintType, p.FLAG_REPEATED),
            2: ('message', p.BytesType, 0),  # required
            3: ('coin_name', p.UnicodeType, 0),  # default=Syscoin
            4: ('script_type', p.UVarintType, 0),  # default=SPENDADDRESS
        }
