from robo_tests.fixtures import robo_run
import json
import os
from typing import List


def test_colect_tasks(datadir):
    from robo._collect_tasks import collect_tasks

    tasks = tuple(collect_tasks(datadir, "main"))
    assert len(tasks) == 1

    tasks = tuple(collect_tasks(datadir, ""))
    assert len(tasks) == 3
    assert {t.name for t in tasks} == {"main", "sub", "main_errors"}
    name_to_task = dict((t.name, f"{t.package_name}.{t.name}") for t in tasks)
    assert name_to_task == {
        "main": "tasks.main",
        "sub": "sub.sub_task.sub",
        "main_errors": "tasks.main_errors",
    }

    tasks = tuple(collect_tasks(datadir, "not_there"))
    assert len(tasks) == 0


def test_collect_tasks_integrated_error(tmpdir):
    result = robo_run(
        ["run", "dir_not_there", "-t=main"], returncode=1, cwd=str(tmpdir)
    )

    decoded = result.stderr.decode("utf-8", "replace")
    if "dir_not_there does not exist" not in decoded:
        raise AssertionError(f"Unexpected stderr: {decoded}")


def verify_log_messages(log_html, expected):
    from robocorp_logging import iter_decoded_log_format_from_log_html

    log_messages = tuple(iter_decoded_log_format_from_log_html(log_html))
    for log_msg in log_messages:
        for expected_dct in expected:
            for key, val in expected_dct.items():
                if log_msg.get(key) != val:
                    break
            else:
                expected.remove(expected_dct)

    if expected:
        new_line = "\n"
        raise AssertionError(
            f"Did not find {expected}.\nFound:\n{new_line.join(str(x) for x in log_messages)}"
        )


def verify_log_messages_from_str(s, expected) -> List[dict]:
    log_messages = []
    for log_msg in s.splitlines():
        log_msg = json.loads(log_msg.strip())
        log_messages.append(log_msg)

    for log_msg in log_messages:
        for expected_dct in expected:
            for key, val in expected_dct.items():
                if log_msg.get(key) != val:
                    break
            else:
                expected.remove(expected_dct)
                break

    if expected:
        new_line = "\n"
        raise AssertionError(
            f"Did not find {expected}.\nFound:\n{new_line.join(str(x) for x in log_messages)}"
        )
    return log_messages


def test_collect_tasks_integrated(datadir):
    result = robo_run(["run", str(datadir), "-t", "main"], returncode=0, cwd=datadir)

    assert (
        not result.stderr
    ), f"Error with command line: {result.args}: {result.stderr.decode('utf-8', 'replace')}"
    assert "In some method" in result.stdout.decode("utf-8")

    # That's the default.
    log_html = datadir / "output" / "log.html"
    assert log_html.exists(), "log.html not generated."
    verify_log_messages(
        log_html,
        [
            dict(message_type="SK", name="some_method"),
            dict(message_type="ST"),
            dict(message_type="ET"),
            dict(message_type="SS"),
            dict(message_type="ES"),
        ],
    )


def test_list_tasks_api(datadir, tmpdir, data_regression):
    def check(result):
        output = result.stdout.decode("utf-8")
        loaded = json.loads(output)
        assert len(loaded) == 3
        for entry in loaded:
            entry["file"] = os.path.basename(entry["file"])
        data_regression.check(loaded)

    # List with the dir as a target
    result = robo_run(["list", str(datadir)], returncode=0, cwd=str(tmpdir))
    check(result)

    # List without the dir as a target (must have the same output).
    result = robo_run(["list"], returncode=0, cwd=datadir)
    check(result)


def test_provide_output_in_stdout(datadir, tmpdir):
    result = robo_run(
        ["run", "-t=main", str(datadir), "--output", str(tmpdir)],
        returncode=0,
        additional_env={"RC_LOG_OUTPUT_STDOUT": "1"},
    )

    verify_log_messages_from_str(
        result.stdout.decode("utf-8"),
        [
            dict(message_type="SK", name="some_method"),
            dict(message_type="ST"),
            dict(message_type="ET"),
            dict(message_type="SS"),
            dict(message_type="ES"),
        ],
    )


def test_error_in_stdout(datadir, tmpdir):
    result = robo_run(
        ["run", "-t=main_errors", str(datadir), "--output", str(tmpdir)],
        returncode=1,
        additional_env={"RC_LOG_OUTPUT_STDOUT": "1"},
    )

    msgs = verify_log_messages_from_str(
        result.stdout.decode("utf-8"),
        [
            dict(message_type="SK", name="main_errors"),
            dict(message_type="ST"),
            dict(message_type="ET"),
            dict(message_type="SS"),
            dict(message_type="ES"),
            dict(message_type="STB"),
        ],
    )

    assert str(msgs).count("STB") == 1, "Only one Start Traceback message expected."
