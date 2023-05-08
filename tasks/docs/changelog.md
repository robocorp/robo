NEXT
-----------------------------

- New argument: `--no-status-rc`:
    When set, if running tasks has an error inside the task the return code of the process is 0 (
    if unsed the return code if an error is thrown inside a task the return code is 1).


0.1.7
-----------------------------

- Provide output in the console showing that a task is being run and the result of the run.
- Redirecting messages written to the console to log messages.
    The `--console-colors` arguments can be set to `auto` (where it'll decide the best approach to print with colors), `plain` to disable the colors or `ansi` to force colors to be printed with ansi chars.
- It's possible to setup the messages redirection by using either command line arguments (`--log-output-to-stdout=json`) or the `RC_LOG_OUTPUT_STDOUT=json` environment variable.
- Upgraded `robocorp-log` dependency to `0.0.15`. 


0.1.6
-----------------------------

- Fixed case where the log would not be properly setup if `[tool.robocorp.log`] was not in `pyproject.toml`.
- Upgraded `robocorp-log` dependency to `0.0.13`. 

0.1.5
-----------------------------

- First alpha release for `robocorp-tasks`.
- `@task` decorator to define entry points.
- Automatic logging 
    - Configures `robocorp-log` with reasonable defaults.
        - Rotate files after 5 files
        - Up to 1MB each
        - Log to `output`
        - Provide `output/log.html` when run finishes.
    - Log customization through `pyproject.toml`.
- Command line API which allows listing tasks with:
    - python -m robocorp.tasks list <directory>
- Command line API which allows running tasks with:
    - python -m robocorp.tasks run <directory> -t <task_name>