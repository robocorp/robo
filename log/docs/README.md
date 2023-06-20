<!-- markdownlint-disable -->

# API Overview

## Modules

- [`robocorp.log`](./robocorp.log.md#module-robocorplog)
- [`robocorp.log.console`](./robocorp.log.console.md#module-robocorplogconsole)
- [`robocorp.log.protocols`](./robocorp.log.protocols.md#module-robocorplogprotocols)
- [`robocorp.log.redirect`](./robocorp.log.redirect.md#module-robocorplogredirect)

## Classes

- [`log.ConsoleMessageKind`](./robocorp.log.md#class-consolemessagekind)
- [`protocols.IReadLines`](./robocorp.log.protocols.md#class-ireadlines)
- [`protocols.Status`](./robocorp.log.protocols.md#class-status)

## Functions

- [`log.add_in_memory_log_output`](./robocorp.log.md#function-add_in_memory_log_output): Adds a log output which is in-memory (receives a callable).
- [`log.add_log_output`](./robocorp.log.md#function-add_log_output): Adds a log output which will write the contents to the given output directory.
- [`log.add_sensitive_variable_name`](./robocorp.log.md#function-add_sensitive_variable_name): Marks a given variable name as sensitive
- [`log.add_sensitive_variable_name_pattern`](./robocorp.log.md#function-add_sensitive_variable_name_pattern): Adds a given pattern to consider a variable name as sensitive.
- [`log.close_log_outputs`](./robocorp.log.md#function-close_log_outputs): This method must be called to close loggers.
- [`log.console_message`](./robocorp.log.md#function-console_message):     Shows a message in the console and also adds it to the log output.
- [`log.critical`](./robocorp.log.md#function-critical): Adds a new logging message with a critical (error) level.
- [`log.end_run`](./robocorp.log.md#function-end_run): Finishes a run session (adds the related event to the log).
- [`log.end_task`](./robocorp.log.md#function-end_task): Ends a task (adds the related event to the log).
- [`log.exception`](./robocorp.log.md#function-exception): Adds to the logging the exceptions that's currently raised.
- [`log.hide_from_output`](./robocorp.log.md#function-hide_from_output): Should be called to hide sensitive information from appearing in the output.
- [`log.html`](./robocorp.log.md#function-html): Adds html contents to the log.
- [`log.info`](./robocorp.log.md#function-info): Adds a new logging message with an info level.
- [`log.is_sensitive_variable_name`](./robocorp.log.md#function-is_sensitive_variable_name): Returns true if the given variable name should be considered sensitive.
- [`log.iter_decoded_log_format_from_log_html`](./robocorp.log.md#function-iter_decoded_log_format_from_log_html): Reads the data saved in the log html and provides decoded messages (dicts).
- [`log.iter_decoded_log_format_from_stream`](./robocorp.log.md#function-iter_decoded_log_format_from_stream): Iterates stream contents and decodes those as dicts.
- [`log.process_snapshot`](./robocorp.log.md#function-process_snapshot): Makes a process snapshot and adds it to the logs.
- [`log.setup_auto_logging`](./robocorp.log.md#function-setup_auto_logging): Sets up automatic logging.
- [`log.setup_log`](./robocorp.log.md#function-setup_log): Setups the log "general" settings.
- [`log.start_run`](./robocorp.log.md#function-start_run): Starts a run session (adds the related event to the log).
- [`log.start_task`](./robocorp.log.md#function-start_task): Starts a task (adds the related event to the log).
- [`log.suppress`](./robocorp.log.md#function-suppress): API to suppress logging to be used as a context manager or decorator.
- [`log.suppress_methods`](./robocorp.log.md#function-suppress_methods): Can be used as a context manager or decorator so that methods are not logged.
- [`log.suppress_variables`](./robocorp.log.md#function-suppress_variables): Can be used as a context manager or decorator so that variables are not logged.
- [`log.verify_log_messages_from_decoded_str`](./robocorp.log.md#function-verify_log_messages_from_decoded_str): Verifies whether the given messages are available or not in the decoded messages.
- [`log.verify_log_messages_from_log_html`](./robocorp.log.md#function-verify_log_messages_from_log_html): Verifies whether the given messages are available or not in the decoded messages.
- [`log.verify_log_messages_from_messages_iterator`](./robocorp.log.md#function-verify_log_messages_from_messages_iterator): Helper for checking that the expected messages are found in the given messages iterator.
- [`log.verify_log_messages_from_stream`](./robocorp.log.md#function-verify_log_messages_from_stream): Verifies whether the given messages are available or not in the decoded messages.
- [`log.warn`](./robocorp.log.md#function-warn): Adds a new logging message with a warn level.
- [`console.set_color`](./robocorp.log.console.md#function-set_color): To be used as:
- [`console.set_mode`](./robocorp.log.console.md#function-set_mode): Can be used to set the mode of the console.
- [`redirect.setup_stdout_logging`](./robocorp.log.redirect.md#function-setup_stdout_logging): This function is responsible for setting up the needed stdout/stderr


---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
