import datetime
import json
from typing import Optional, List, Callable, Any, Dict, Iterator
from .protocols import IReadLines


class Decoder:
    def __init__(self) -> None:
        self.memo: Dict[str, str] = {}

    def decode_message_type(self, message_type: str, message: str) -> Optional[dict]:
        handler = _MESSAGE_TYPE_INFO[message_type]
        ret = {"message_type": message_type}
        try:
            r = handler(self, message)
            if not r:
                if message_type == "M":
                    return None
                raise RuntimeError(
                    f"No return when decoding: {message_type} - {message}"
                )
                if not isinstance(r, dict):
                    ret[
                        "error"
                    ] = f"Expected dict return when decoding: {message_type} - {message}. Found: {ret}"

            ret.update(r)
        except Exception as e:
            ret["error"] = f"Error decoding: {message_type}: {e}"
        return ret


def _decode_oid(decoder: Decoder, oid: str) -> str:
    return decoder.memo[oid]


def _decode_float(decoder: Decoder, msg: str) -> float:
    return float(msg)


def _decode_int(decoder: Decoder, msg: str) -> int:
    return int(msg)


def _decode_str(decoder: Decoder, msg: str) -> str:
    return msg


def _decode(message_definition: str) -> Callable[[Decoder, str], Any]:
    names: List[str] = []
    name_to_decode: dict = {}
    for s in message_definition.split(","):
        s = s.strip()
        i = s.find(":")
        decode = "oid"
        if i != -1:
            s, decode = s.split(":", 1)
        names.append(s)
        if decode == "oid":
            name_to_decode[s] = _decode_oid

        elif decode == "int":
            name_to_decode[s] = _decode_int

        elif decode == "float":
            name_to_decode[s] = _decode_float

        elif decode == "str":
            name_to_decode[s] = _decode_str

        else:
            raise RuntimeError(f"Unexpected: {decode}")

    def dec_impl(decoder: Decoder, message: str):
        splitted = message.split("|", len(names) - 1)
        ret = {}
        for i, s in enumerate(splitted):
            name = names[i]
            try:
                ret[name] = name_to_decode[name](decoder, s)
            except:
                ret[name] = None
        return ret

    return dec_impl


def decode_time(decoder: Decoder, time: str):
    d: datetime.datetime = datetime.datetime.fromisoformat(time)

    # The internal time is in utc, so, we need to decode it to the current timezone.
    d = d.astimezone()

    return {"initial_time": time}


def decode_memo(decoder: Decoder, message: str) -> None:
    memo_id: str
    memo_value: str

    memo_id, memo_value = message.split(":", 1)

    # Note: while the json.loads could actually load anything, in the spec we only
    # have oid for string messages (which is why it's ok to type it as that).
    memo_value = json.loads(memo_value)
    decoder.memo[memo_id] = memo_value


# Whenever the decoding changes we should bump up this version.
DOC_VERSION = "0.0.1"

MESSAGE_TYPE_YIELD_RESUME = "YR"
MESSAGE_TYPE_YIELD_SUSPEND = "YS"
MESSAGE_TYPE_YIELD_FROM_RESUME = "YFR"
MESSAGE_TYPE_YIELD_FROM_SUSPEND = "YFS"

_MESSAGE_TYPE_INFO: Dict[str, Callable[[Decoder, str], Any]] = {
    # Version of the log output
    "V": _decode("version:str"),
    # Some information message
    "I": lambda _decoder, message: {"info": json.loads(message)},
    # The log has an id that may be split into multiple parts.
    "ID": _decode("part:int, id:str"),
    # Time.
    "T": decode_time,
    # Memorize some word to be used as oid.
    "M": decode_memo,
    # Log (raw text)
    "L": _decode(
        "level:str, message:oid, source:oid, lineno:int, time_delta_in_seconds:float"
    ),
    # Log (html)
    "LH": _decode(
        "level:str, message:oid, source:oid, lineno:int, time_delta_in_seconds:float"
    ),
    # Start Run
    "SR": _decode(
        "name:oid, time_delta_in_seconds:float",
    ),
    # End Run
    "ER": _decode("status:oid, time_delta_in_seconds:float"),
    # Start Task
    "ST": _decode(
        "name:oid, libname:oid, source:oid, lineno:int, time_delta_in_seconds:float",
    ),
    # End Task
    "ET": _decode("status:oid, message:oid, time_delta_in_seconds:float"),
    # Start Element (some element we're tracking such as method, for, while, etc).
    "SE": _decode(
        "name:oid, libname:oid, type:oid, doc:oid, source:oid, lineno:int, time_delta_in_seconds:float",
    ),
    # Yield Resume (coming back to a suspended frame).
    MESSAGE_TYPE_YIELD_RESUME: _decode(
        "name:oid, libname:oid, source:oid, lineno:int, time_delta_in_seconds:float",
    ),
    # Yield From Resume (coming back to a suspended frame).
    MESSAGE_TYPE_YIELD_FROM_RESUME: _decode(
        "name:oid, libname:oid, source:oid, lineno:int, time_delta_in_seconds:float",
    ),
    # End Element
    "EE": _decode("type:oid, status:oid, time_delta_in_seconds:float"),
    # Yield Suspend (pausing a frame)
    MESSAGE_TYPE_YIELD_SUSPEND: _decode(
        "name:oid, libname:oid, source:oid, lineno:int, type:oid, value:oid, time_delta_in_seconds:float",
    ),
    # Yield From Suspend (pausing a frame)
    MESSAGE_TYPE_YIELD_FROM_SUSPEND: _decode(
        "name:oid, libname:oid, source:oid, lineno:int, time_delta_in_seconds:float",
    ),
    # Assign
    "AS": _decode(
        "source:oid, lineno:int, target:oid, type:oid, value:oid, time_delta_in_seconds:float"
    ),
    # Element/method argument (name and value of the argument).
    "EA": _decode("name:oid, type:oid, value:oid"),
    # Tag the current scope with some value.
    "TG": _decode("tag:oid"),
    # Set some time for the current scope.
    "S": _decode("start_time_delta:float"),
    # --------------------------------------------------------------- Tracebacks
    # Start traceback with the exception error message.
    # Note: it should be possible to start a traceback inside another traceback
    # for cases where the exception has an exception cause.
    # Start Traceback
    "STB": _decode(
        "message:oid, time_delta_in_seconds:float",
    ),
    # Traceback Entry
    "TBE": _decode(
        "source:oid, lineno:int, method:oid, line_content:oid",
    ),
    # Traceback variable
    "TBV": _decode(
        "name:oid, type:oid, value:oid",
    ),
    # End Traceback
    "ETB": _decode(
        "time_delta_in_seconds:float",
    ),
}

_MESSAGE_TYPE_INFO["RR"] = _MESSAGE_TYPE_INFO["SR"]
_MESSAGE_TYPE_INFO["RT"] = _MESSAGE_TYPE_INFO["ST"]
_MESSAGE_TYPE_INFO["RE"] = _MESSAGE_TYPE_INFO["SE"]
_MESSAGE_TYPE_INFO["RTB"] = _MESSAGE_TYPE_INFO["STB"]
_MESSAGE_TYPE_INFO["RYR"] = _MESSAGE_TYPE_INFO["YR"]


def iter_decoded_log_format(stream: IReadLines) -> Iterator[dict]:
    decoder: Decoder = Decoder()
    line: str
    message_type: str
    message: str
    decoded: Optional[dict]

    for line in stream.readlines():
        line = line.strip()
        if line:
            try:
                message_type, message = line.split(" ", 1)
            except:
                raise RuntimeError(f"Error decoding line: {line}")
            decoded = decoder.decode_message_type(message_type, message)
            if decoded:
                yield decoded
