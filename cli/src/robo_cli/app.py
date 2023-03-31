import glob
import time
from pathlib import Path

import typer
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from robo_cli import environment, rcc, templates
from robo_cli.process import Process, ProcessError

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def new():
    """Creates a new project"""
    console.print()
    console.print("This command will guide you through creating your project")
    console.print()

    project_name = Prompt.ask("[cyan]Project name", default="example")
    project_root = Path(project_name)
    if project_root.exists():
        console.print(f"Project folder '{project_root}' already exists!")
        raise typer.Exit(code=1)

    choices = templates.list_templates()
    template = Prompt.ask(
        "[cyan]Project template",
        choices=choices,
        default="blank",
    )

    console.print()
    console.print("Initializing project")
    path = templates.copy_template(Path(project_name), template=template)
    console.print()
    console.print("✨ Project created ✨")
    console.print()
    console.print(f"Project path: {path.absolute()}")
    console.print()
    console.print("Configuration file: [bold]pyproject.toml[/bold]")
    console.print("Tasks file: [bold]tasks.py[/bold]")


def robot_run():
    spinner = Spinner("dots", "Running [bold]check-website[/bold]...")
    yield spinner

    time.sleep(2)

    steps = [
        "browser.open()",
        'browser.goto("http://robocorp.com")',
        "browser.take_screenshot()",
    ]

    status_spinner = Spinner("dots")

    for prog in range(len(steps)):
        table = Table()
        table.add_column("Status")
        table.add_column("Keyword")
        for idx in range(prog + 1):
            step = steps[idx]
            table.add_row("🟢" if idx < prog else status_spinner, step)

        yield Group(table, spinner)
        time.sleep(2)

    table = Table()
    table.add_column("Status")
    table.add_column("Keyword")
    for step in steps:
        table.add_row("🟢", step)

    yield table


@app.command()
def run():
    """Runs the robot from current directory"""
    try:
        with console.status("Building environment"):
            env = environment.ensure()

        with console.status("Running robot"):
            # TODO: Figure out what to call from inner framework
            proc = Process(["python", "tasks.py"], env=env)
            proc.on_stdout(lambda line: console.print(line))
            proc.run()

    except ProcessError as exc:
        console.print(exc.stderr)
        console.print("---")
        console.print("Run failed due to unexpected error")
        raise typer.Exit(code=1)

    artifacts = glob.glob("output/*")
    console.print(
        Panel.fit(
            Group(*artifacts),
            title="Artifacts",
        )
    )

    console.print()
    console.print("Run [bold]<taskname>[/bold] successful!")
    console.print()


@app.command()
def export():
    """Exports the robot from current directory. Can be used to inspect what contents
    will be deployed to the cloud.
    """
    console.print()
    with console.status("Exporting robot"):
        path = rcc.robot_wrap()

    console.print(f"Exported to {path}")
    console.print()


@app.command()
def deploy():
    """Deploys the robot from current directory"""
    console.print()
    console.print()

    with console.status("Fetching workspace list"):
        available_workspaces = rcc.cloud_workspace()

    workspace_names = list(available_workspaces.keys())
    keys = [str(i + 1) for i in range(0, len(workspace_names))]
    console.print("Available workspaces:")
    i = 1
    for name in workspace_names:
        console.print(f"{i}. {name}")
        i = i + 1
    workspace_index = IntPrompt.ask("Workspace to deploy into?", choices=keys) - 1
    selected_workspace = available_workspaces[workspace_names[workspace_index]]
    workspace_id = selected_workspace["id"]
    workspace_url = selected_workspace["url"]
    # TODO: have option to select from list of robot ids or create new one
    robot_id = Prompt.ask("Robot id to deploy with?", default="example")

    console.print(
        "Deploying [bold]example[/bold] to "
        + f"[underline]{workspace_url}/robots/{robot_id}/[/underline]"
    )
    console.print()

    # TODO: add an if to check for this. Currently this _only_ works for replacing
    # Confirm.ask("Project already exists, replace?")

    with console.status("Uploading project"):
        console.print(rcc.cloud_push(workspace_id, robot_id))

    console.print()
    console.print("Deploy of [bold]example[/bold] successful!")
    console.print(f"Link: [underline]{workspace_url}/robots/{robot_id}/[/underline]")
    console.print()


@app.command()
def list_tasks():
    console.print()
    console.print("> robo run")

    desc = Text.assemble("\nTasks for handling generated report files\n")

    table = Table(title="Tasks")
    table.add_column("ID")
    table.add_column("Name", justify="right", style="cyan", no_wrap=True)
    table.add_column("Description")

    table.add_row("1", "copy-reports", "Copy reports to output")
    table.add_row("2", "remove-reports", "Remove generated reports")

    console.print()
    console.print(Panel.fit(Group(desc, table), title="example"))
    console.print()
    Prompt.ask("Select task to run", choices=["1", "2"])
    console.print()


if __name__ == "__main__":
    app()
