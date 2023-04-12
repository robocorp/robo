from typing import Tuple
from pathlib import Path
import sys
from robo._argdispatch import arg_dispatch
import json
from contextlib import contextmanager
import os


def _setup_log_output(
    output_dir: Path,
    max_file_size: str = "1MB",
    max_files: int = 5,
    log_name: str = "log.html",
):
    import robo_log

    # This can be called after user code is imported (but still prior to its
    # execution).
    return robo_log.add_log_output(
        output_dir=output_dir,
        max_file_size=max_file_size,
        max_files=max_files,
        log_html=output_dir / log_name,
    )


@contextmanager
def _setup_stdout_logging():
    import robo_log
    import threading

    if os.environ.get("RC_LOG_OUTPUT_STDOUT", "").lower() in ("1", "t", "true"):
        original_stdout = sys.stdout

        # Keep printing anything the user provides to the stderr for now.
        # TODO: provide messages given to stdout as expected messages in the output?
        sys.stdout = sys.stderr

        from robo_log._decoder import Decoder

        decoder = Decoder()

        import queue

        q = queue.Queue()

        EXIT = object()

        def in_thread():
            import traceback

            while True:
                msg = q.get(block=True)
                if msg is EXIT:
                    return

                try:
                    line = msg.strip()
                    if line:
                        message_type, message = line.split(" ", 1)
                        decoded = decoder.decode_message_type(message_type, message)
                        if decoded:
                            original_stdout.write(f"{json.dumps(decoded)}\n")
                            # Flush (so, clients don't need to execute as unbuffered).
                            original_stdout.flush()
                except:
                    traceback.print_exc(file=sys.stderr)

        # Note: not daemon, we want all messages to be sent prior to exiting.
        threading.Thread(
            target=in_thread, daemon=False, name="RoboLogStdoutThread"
        ).start()

        def write(msg):
            q.put(msg)

        with robo_log.add_in_memory_log_output(write):
            try:
                yield
            finally:
                q.put(EXIT)
                sys.stdout = original_stdout

    else:
        yield  # Nothing to do but respect the contextmanager.


# Note: the args must match the 'dest' on the configured argparser.
@arg_dispatch.register(name="list")
def list_tasks(
    path: str,
) -> int:
    from robo._collect_tasks import collect_tasks
    from robo._task import Context
    from robo._protocols import ITask

    p = Path(path)
    context = Context()
    if not p.exists():
        context.show_error(f"Path: {path} does not exist")
        return 1

    task: ITask
    tasks_found = []
    for task in collect_tasks(p):
        tasks_found.append(
            {
                "name": task.name,
                "line": task.lineno,
                "file": task.filename,
                "docs": getattr(task.method, "__doc__") or "",
            }
        )

    sys.stdout.write(json.dumps(tasks_found))
    return 0


# Note: the args must match the 'dest' on the configured argparser.
@arg_dispatch.register()
def run(
    output_dir: str,
    path: str,
    task_name: str,
    max_log_files: int = 5,
    max_log_file_size: str = "1MB",
) -> int:
    from robo._collect_tasks import collect_tasks
    from robo._hooks import before_task_run, after_task_run
    from robo._logging_setup import setup_auto_logging
    from robo._protocols import ITask
    from robo._task import Context
    from robo._protocols import Status

    # Don't show internal machinery on tracebacks:
    # setting __tracebackhide__ will make it so that robocorp-logging
    # won't show this frame onwards in the logging.
    __tracebackhide__ = 1

    p = Path(path)
    context = Context()
    if not p.exists():
        context.show_error(f"Path: {path} does not exist")
        return 1

    with setup_auto_logging(), _setup_stdout_logging(), _setup_log_output(
        output_dir=Path(output_dir),
        max_files=max_log_files,
        max_file_size=max_log_file_size,
    ):
        from robo._exceptions import RoboCollectError

        if not task_name:
            context.show(f"\nCollecting tasks from: {path}")
        else:
            context.show(f"\nCollecting task {task_name} from: {path}")

        try:
            tasks: Tuple[ITask, ...] = tuple(collect_tasks(p, task_name))
        except RoboCollectError as e:
            context.show_error(str(e))
            return 1

        if not tasks:
            context.show(f"Did not find any tasks in: {path}")
            return 1

        for task in tasks:
            before_task_run(task)
            try:
                task.run()
                task.status = Status.PASS
            except Exception as e:
                task.status = Status.ERROR
                task.message = str(e)
            finally:
                after_task_run(task)

            returncode = 0 if task.status == Status.PASS else 1
            return returncode

        raise AssertionError("Should never get here.")


def main(args=None, exit: bool = True) -> int:
    if args is None:
        args = sys.argv[1:]
    returncode = arg_dispatch.process_args(args)
    if exit:
        sys.exit(returncode)
    return returncode


if __name__ == "__main__":
    main()