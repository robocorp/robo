from contextlib import contextmanager
from io import StringIO
from pathlib import Path

import datetime
import json
import functools
import sys
import threading
import typing
import weakref

from typing import (
    Optional,
    Any,
    Iterator,
    List,
    Sequence,
    Dict,
    Union,
    Iterable,
    Literal,
    overload,
    Callable,
    Protocol,
)
from ._logger_instances import _get_logger_instances
from .protocols import OptExcInfo, LogHTMLStyle, Status, IReadLines
from ._suppress_helper import SuppressHelper as _SuppressHelper


if typing.TYPE_CHECKING:
    from ._robo_logger import _RoboLogger

__version__ = "0.0.13"
version_info = [int(x) for x in __version__.split(".")]

from . import _config

# --- Make these a part of the public API.

Filter = _config.Filter
FilterKind = _config.FilterKind
BaseConfig = _config.BaseConfig
ConfigFilesFiltering = _config.ConfigFilesFiltering


# --- Logging methods for custom messaging.


def _log(level, message: Sequence[Any], html: bool = False) -> None:
    back_frame = sys._getframe(2)
    source = back_frame.f_code.co_filename
    lineno = back_frame.f_lineno

    m = " ".join(str(x) for x in message)
    for robo_logger in _get_logger_instances():
        robo_logger.log_message(level, m, html, source, lineno)


def critical(*message: Any) -> None:
    """
    Adds a new logging message with a critical (error) level.

    Args:
        message: The message which should be logged.
        html: If True the message passed should be rendered as HTML.

    Example:
        critical('Failed because', obj, 'is not', expected)

    Note:
        Formatting converts all objects given to `str`. If you need custom
        formatting please pre-format the string.
        i.e.:
        critical(f'Failed because {obj!r} is not {expected!r}.')
    """
    _log(Status.ERROR, message)


def warn(*message: Any) -> None:
    """
    Adds a new logging message with a warn level.

    Args:
        message: The message which should be logged.
        html: If True the message passed should be rendered as HTML.

    Example:
        warn('Did not expect', obj)

    Note:
        Formatting converts all objects given to `str`. If you need custom
        formatting please pre-format the string.
        i.e.:
        warn(f'Did not expect {obj!r}.')
    """
    _log(Status.WARN, message)


def info(*message: Any) -> None:
    """
    Adds a new logging message with an info level.

    Args:
        message: The message which should be logged.
        html: If True the message passed should be rendered as HTML.


    Example:
        info('Received value', obj)

    Note:
        Formatting converts all objects given to `str`. If you need custom
        formatting please pre-format the string.
        i.e.:
        info(f'Received value {obj!r}.')

    """
    _log(Status.INFO, message)


def exception(*message: Any):
    """
    Adds to the logging the exceptions that's currently raised.

    Args:
        message: If given an additional error message to be shown.
        html: If True the message passed should be rendered as HTML.
    """
    if message:
        _log(Status.ERROR, message)

    exc_info = sys.exc_info()
    for robo_logger in _get_logger_instances():
        robo_logger.log_method_except(exc_info, unhandled=True)


def html(html: str, level: str = "INFO"):
    """
    Adds html contents to the log.

    Args:
        html: The html content to be embedded in the page.
        level: The level of the message ("INFO", "WARN" or "ERROR")

    Example adding an image:

        html(
            '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAnBAMAAACGbbfxAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAbUExURR4nOzpCVI+Tnf///+Pk5qqutXN4hVZdbMbJzod39mUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAETSURBVDjLnZIxT8MwFITPqDQdG1rBGjX8AOBS0hG1ghnUhbFSBlZvMFbqH+fZaeMLBJA4KZHzyb7ce374l1we3vm0Ty/Ix7era1YvSjOeVBWCZx3mveBDwlWyH1OUXM5t0yJqS+4V33xdwWFCrvOoOfmA1r30Z+r9jHV7zmeKd7ADQEOvATkFlzGz13JqIGanYbexYLOldcY+IsniqrEyRrUj7xBwccRm/lSuPqysI3YBjzUfQproNOr/0tLEgE3CK8P2YG54K401XIeWHDw2Uo5H5UP1l1ZXr9+7U2ffRfhTC9HwFVMmqOzl7vTDnEwSvhXsNLaoGbIGurvf97ArhzYbj01sm6TKXm3yC3yX8/hdwCdipl9ujxriXgAAAABJRU5ErkJggg=="/>'
        )
    """

    assert level in ("ERROR", "WARN", "INFO")
    _log(level, (html,), html=True)


# --- Methods related to hiding logging information.


@contextmanager
def _suppress_contextmanager(variables=True, methods=True):
    instances = _get_logger_instances()
    for robo_logger in instances:
        if variables:
            robo_logger.stop_logging_variables()
        if methods:
            robo_logger.stop_logging_methods()

    try:
        yield
    finally:
        for robo_logger in instances:
            if variables:
                robo_logger.start_logging_variables()
            if methods:
                robo_logger.start_logging_methods()


_suppress_helper = _SuppressHelper(_suppress_contextmanager)


def suppress_methods():
    """
    Can be used as a context manager or decorator so that methods are no
    longer logged.

    i.e.:
        @suppress_methods
        def method():
            ...

        or

        with suppress_methods():
            ...
    """
    return suppress(variables=False, methods=True)


def suppress_variables():
    """
    Can be used as a context manager or decorator so that variables are no
    longer logged.

    i.e.:
        @suppress_variables
        def method():
            ...

        or

        with suppress_variables():
            ...
    """
    return suppress(variables=True, methods=False)


class _AnyCall(Protocol):
    def __call__(self, *args, **kwargs) -> Any:
        pass


@overload
def suppress(*, variables: bool = True, methods: bool = True) -> _AnyCall:
    """
    Arguments when used as a decorator or context manager with parameters.

    Suppresses everything except the arguments marked as "False"
    """


@overload
def suppress(func: Callable[[], Any]) -> _AnyCall:
    """
    Arguments when used as a decorator without any arguments (where it just
    receives a function).
    """


def suppress(*args, **kwargs):
    """
    API to suppress logging to be used as a context manager or decorator.

    By default suppresses everything and its actual API is something as:

    def suppress(variables:bool = True, methods:bool = True):
        ...

    Args:
        variables: Whether variables should be suppressed in the scope.

        methods: Whether method calls should be suppressed in the scope.

    Usage as a decorator:

        from robocorp import log

        @log.suppress
        def func():
            ....

    Usage as a decorator suppressing only variables:

        from robocorp import log

        @log.suppress(methods=False)
        def func():
            ....

    Usage as a context manager:

        from robocorp import log

        with log.suppress(methods=False):
            ....
    """
    return _suppress_helper.handle(*args, **kwargs)


from ._sensitive_variable_names import (
    SensitiveVariableNames as _SensitiveVariableNames,
)

_sensitive_names = _SensitiveVariableNames(("password", "passwd"))


def is_sensitive_variable_name(variable_name: str) -> bool:
    """
    Args:
        variable_name: The variable name to be checked.

    Returns:
        True if the given variable name is considered to be sensitive (in which
        case its value should be redacted) and False otherwise.
    """
    return _sensitive_names.is_sensitive_variable_name(variable_name)


def add_sensitive_variable_name(variable_name: str) -> None:
    """
    Marks a given variable name as sensitive (in which case any variable
    containing the given `variable_name` will be redacted).

    Note that this will add a patterns where any variable containing the given
    variable name even as a substring will be considered sensitive.

    Args:
        variable_name: The variable name to be considered sensitive.
    """
    _sensitive_names.add_sensitive_variable_name(variable_name)


def add_sensitive_variable_name_pattern(variable_name_pattern: str) -> None:
    """
    Adds a given pattern to consider a variable name as sensitive. Any variable
    name matching the given pattern will have its value redacted.

    Args:
        variable_name_pattern: The variable name pattern to be considered
        sensitive.
    """
    _sensitive_names.add_sensitive_variable_name_pattern(variable_name_pattern)


def hide_from_output(string_to_hide: str) -> None:
    """
    Should be called to hide sensitive information from appearing in the output.

    Note that any variable assign or argument which is set to a name containing
    the string:

    'password' or 'passwd'

    Will be automatically hidden and it's also possible to add new names to
    be automatically redacted withe the methods: `add_sensitive_variable_name`
    and `add_sensitive_variable_name_pattern`.

    Args:
        string_to_hide: The string that should be hidden from the output.
    """
    for robo_logger in _get_logger_instances():
        robo_logger.hide_from_output(string_to_hide)


# --- Logging methods usually called automatically from the framework.


def start_run(name: str) -> None:
    """
    Starts a run session (adds the related event to the log).

    Args:
        name: The name of the run.

    Note: robocorp-tasks calls this method automatically.
    """
    for robo_logger in _get_logger_instances():
        robo_logger.start_run(name)


def end_run(name: str, status: str) -> None:
    """
    Finishes a run session (adds the related event to the log).

    Args:
        name: The name of the run.
        status: The run status.

    Note: robocorp-tasks calls this method automatically.
    """
    for robo_logger in _get_logger_instances():
        robo_logger.end_run(name, status)


def start_task(name: str, libname: str, source: str, lineno: int) -> None:
    """
    Starts a task (adds the related event to the log).

    Args:
        name: The name of the task.
        libname: The library (module name) where the task is defined.
        source: The source of the task.
        lineno: The line number of the task in the given source.

    Note: robocorp-tasks calls this method automatically.
    """
    for robo_logger in _get_logger_instances():
        robo_logger.start_task(name, libname, source, lineno)


def end_task(name: str, libname: str, status: str, message: str) -> None:
    """
    Ends a task (adds the related event to the log).

    Args:
        name: The name of the task.
        libname: The library (module name) where the task is defined.
        status: The source of the task.
        message: The line number of the task in the given source.

    Note: robocorp-tasks calls this method automatically.
    """
    for robo_logger in _get_logger_instances():
        robo_logger.end_task(name, libname, status, message)


# ---- APIs to decode existing log files


def iter_decoded_log_format_from_stream(stream: IReadLines) -> Iterator[dict]:
    """
    Args:
        stream: The stream which should be iterated in (anything with a
            `readlines()` method which should provide the messages encoded
            in the internal format).

    Returns:
        An iterator which will decode the messages and provides a dictionary for
        each message found.

        Example of messages provided:

        {'message_type': 'V', 'version': '1'}
        {'message_type': 'T', 'initial_time': '2022-10-31T07:45:57.116'}
        {'message_type': 'ID', 'part': 1, 'id': 'gen-from-output-xml'}
        {'message_type': 'SR', 'name': 'Robot Check', 'time_delta_in_seconds': 0.3}
        ...

        Note: the exact format of the messages provided is not stable across
        releases.
    """
    from ._decoder import iter_decoded_log_format

    return iter_decoded_log_format(stream)


def iter_decoded_log_format_from_log_html(log_html: Path) -> Iterator[dict]:
    """
    This function will read the data saved in the log html and provide an
    iterator which will provide the decoded messages which were encoded into it.

    Returns:
        An iterator which will decode the messages and provides a dictionary for
        each message found.

        Example of messages provided:

        {'message_type': 'V', 'version': '1'}
        {'message_type': 'T', 'initial_time': '2022-10-31T07:45:57.116'}
        {'message_type': 'ID', 'part': 1, 'id': 'gen-from-output-xml'}
        {'message_type': 'SR', 'name': 'Robot Check', 'time_delta_in_seconds': 0.3}
        ...

        Note: the exact format of the messages provided is not stable across
        releases.
    """
    import zlib
    import base64
    from ast import literal_eval

    txt = log_html.read_text(encoding="utf-8")
    i = txt.find("let chunks = [")
    j = txt.find("];", i)

    if i < 0 or j < 0:
        # It may be that we're in dev mode and the target should be the bundle.js
        bundle_js = log_html.parent / "bundle.js"
        if bundle_js.exists():
            txt = bundle_js.read_text(encoding="utf-8")
            i = txt.find("let chunks = [")
            j = txt.find("];", i)

    assert i > 0, "Could not find the chunks in the file."
    assert j > 0, "Could not find the end of the chunks in the file."

    sub = txt[i + len("let chunks = ") : j + 1]
    # We have something as:
    # ['base64strZippedStr', 'base64strZippedStr']
    # so, at this point decode it and unzip it
    lst = literal_eval(sub)

    stream = StringIO()
    for s in lst:
        decoded = zlib.decompress(base64.b64decode(s))
        stream.write(decoded.decode("utf-8"))

    stream.seek(0)
    yield from iter_decoded_log_format_from_stream(stream)


_DEFAULT_NOT_EXPECTED: Sequence[dict] = ({"message_type": "L", "level": "E"},)


def verify_log_messages_from_messages_iterator(
    messages_iterator: Iterator[dict],
    expected: Sequence[dict],
    not_expected: Sequence[dict] = _DEFAULT_NOT_EXPECTED,
) -> List[dict]:
    """
    A helper for checking that the expected messages are found (or not found) in
    the given messages iterator.

    Args:
        messages_iterator: An iterator over the messages found.
        expected: The messages which are expected to be found. If some message
            expected to be found is not found an AssertionError will be raised.
        not_expected: The messages that should not appear.

    Example:
        verify_log_messages_from_messages_iterator(
        messages_iterator,
        [
            {'message_type': 'V', 'version': '1'}
            {'message_type': 'T', 'initial_time': '2022-10-31T07:45:57.116'}
        ]

    Note: if one of the key entries is `__check__` the value will be considered
    a callable which should return `True` or `False` to determine if a match was
    made.

    Example:
        verify_log_messages_from_messages_iterator(
        messages_iterator,
        [
            {
                "message_type": "T",
                # i.e.: check for the utc timezone (+00:00) in the time.
                "__check__": lambda msg: msg["initial_time"].endswith("+00:00"),
            },
        ]
    """
    expected_lst: List[dict] = list(expected)
    log_messages = list(messages_iterator)
    log_msg: dict
    for log_msg in log_messages:
        for not_expected_dct in not_expected:
            for key, val in not_expected_dct.items():
                if key == "__check__":
                    if not val(log_msg):
                        break

                elif log_msg.get(key) != val:
                    break
            else:
                new_line = "\n"
                raise AssertionError(
                    f"Found unexpected message: {not_expected_dct}.\nFound:\n{new_line.join(str(x) for x in log_messages)}"
                )

        for expected_dct in expected_lst:
            for key, val in expected_dct.items():
                if key == "__check__":
                    if not val(log_msg):
                        break

                elif log_msg.get(key) != val:
                    break
            else:
                expected_lst.remove(expected_dct)
                break

    if expected_lst:
        new_line = "\n"
        raise AssertionError(
            f"Did not find {expected_lst}.\nFound:\n{new_line.join(str(x) for x in log_messages)}"
        )
    return log_messages


def verify_log_messages_from_decoded_str(
    s: str,
    expected: Sequence[dict],
    not_expected: Sequence[dict] = _DEFAULT_NOT_EXPECTED,
) -> List[dict]:
    """
    Args:
        s: A string with the messages already decoded (where messages are
        separated by lines and each message is a json string to be decoded).
        expected: The messages expected.
        not_expected: The messages that should not appear.

    See: `verify_log_messages_from_messages_iterator` for more details on the
        matching of messages.
    """
    log_messages: List[dict] = []
    for log_msg in s.splitlines():
        log_msg_dict: dict = json.loads(log_msg.strip())
        log_messages.append(log_msg_dict)

    return verify_log_messages_from_messages_iterator(
        iter(log_messages), expected, not_expected
    )


def verify_log_messages_from_log_html(
    log_html: Path,
    expected: Sequence[dict],
    not_expected: Sequence[dict] = _DEFAULT_NOT_EXPECTED,
) -> List[dict]:
    """
    Args:
        log_html: The path to the log_html where messages were embedded.
        expected: The messages expected.
        not_expected: The messages that should not appear.

    See: `verify_log_messages_from_messages_iterator` for more details on the
        matching of messages.
    """
    iter_in = iter_decoded_log_format_from_log_html(log_html)
    return verify_log_messages_from_messages_iterator(iter_in, expected, not_expected)


def verify_log_messages_from_stream(
    stream: IReadLines,
    expected: Sequence[dict],
    not_expected: Sequence[dict] = _DEFAULT_NOT_EXPECTED,
) -> Sequence[dict]:
    """
    Args:
        stream: A stream from where the encoded messages are expected to be read
            from.
        expected: The messages expected.
        not_expected: The messages that should not appear.

    See: `verify_log_messages_from_messages_iterator` for more details on the
        matching of messages.
    """
    return verify_log_messages_from_messages_iterator(
        iter_decoded_log_format_from_stream(stream), expected, not_expected
    )


# --- APIs to setup the logging


def setup_auto_logging(config: Optional[BaseConfig] = None):
    """
    Sets up automatic logging.

    This must be called prior to actually importing the modules which should
    be automatically logged.

    Args:
        config: The configuration specifying how modules should be automatically
            logged.

            If not passed, by default all files which are library files (i.e.:
            in the python `Lib` or `site-packages`) won't be logged and all files
            which are not library files will be fully logged.

    Returns a context manager which will stop applying the auto-logging to new
    loaded modules. Note that modules which are already being tracked won't
    stop being tracked.
    """
    from ._auto_logging_setup import register_auto_logging_callbacks

    use_config: BaseConfig
    if config is None:
        # If not passed, use default.
        use_config = ConfigFilesFiltering()
    else:
        use_config = config

    return register_auto_logging_callbacks(use_config)


def add_log_output(
    output_dir: Union[str, Path],
    max_file_size: str = "1MB",
    max_files: int = 5,
    log_html: Optional[Union[str, Path]] = None,
    log_html_style: LogHTMLStyle = "standalone",
):
    """
    Adds a log output which will write the contents to the given output
    directory. Optionally it's possible to collect all the output when the run
    is finished and put it into a log.html file.

    Args:
        output_dir: The output directory where the log contents should be saved.
        max_file_size: The maximum file size for one log file.
        max_files: The maximum amount of files which can be added (if more would
            be needed the oldest one is erased).
        log_html: If given this is the path (file) where the log.html contents
            should be written (the log.html will include all the logs from the
            run along with a viewer for such logs).
        log_html_style: The style to be used for the log.html.

    Note:
        It's Ok to add more than one log output, but if 2 log outputs point
        to the same directory there will be conflicts (in the future this should
        generate an error).
    """
    from ._robo_logger import _RoboLogger  # @Reimport
    from ._auto_logging_setup import OnExitContextManager

    if not output_dir:
        raise RuntimeError("The output directory must be specified.")

    logger = _RoboLogger(
        output_dir, max_file_size, max_files, log_html, log_html_style=log_html_style
    )
    _get_logger_instances()[logger] = 1

    def _exit():
        _get_logger_instances().pop(logger, None)
        logger.close()

    return OnExitContextManager(_exit)


def close_log_outputs():
    """
    This method must be called to close loggers (note that some loggers such as
    the one which outputs html needs to bo closed to actually write the output).
    """
    while _get_logger_instances():
        logger = next(iter(_get_logger_instances()))
        _get_logger_instances().pop(logger, None)
        logger.close()


def add_in_memory_log_output(write):
    """
    Adds a log output which is in-memory.

    Args:
        write: A callable which will be called as `write(msg)` whenever
        a message is sent from the logging.

    Returns:
        A context manager which can be used to automatically remove and
        close the related logger.
    """
    from ._robo_logger import _RoboLogger  # @Reimport
    from ._auto_logging_setup import OnExitContextManager

    logger = _RoboLogger(__write__=write)
    _get_logger_instances()[logger] = 1

    def _exit():
        _get_logger_instances().pop(logger, None)
        logger.close()

    return OnExitContextManager(_exit)


# --- Private APIs

# Not part of the API, used to determine whether a file is a project file
# or a library file when running with the FilterKind.log_on_project_call kind.
from ._rewrite_filtering import FilesFiltering

_files_filtering = FilesFiltering()
_in_project_roots = _files_filtering.in_project_roots


def _caller_in_project_roots() -> bool:
    try:
        return _in_project_roots(sys._getframe(2).f_code.co_filename)
    except ValueError:  # call stack is not deep enough
        return False
