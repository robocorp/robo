import urllib.request
import os
import platform
import shutil
import stat
import sys
from contextlib import contextmanager
from itertools import chain
from pathlib import Path
from typing import Optional

from invoke import task

CURDIR = Path(__file__).parent
BUILD = CURDIR / "build"
BIN = CURDIR / "include" / "bin"
TEMPLATES = CURDIR / "include" / "templates"
TIMESTAMP = CURDIR / ".timestamp"

RCC_VERSION = "14.6.0"
RCC_URLS = {
    "Windows": f"https://downloads.robocorp.com/rcc/releases/v{RCC_VERSION}/windows64/rcc.exe",
    "Darwin": f"https://downloads.robocorp.com/rcc/releases/v{RCC_VERSION}/macos64/rcc",
    "Linux": f"https://downloads.robocorp.com/rcc/releases/v{RCC_VERSION}/linux64/rcc",
}


def run(ctx, *parts):
    args = " ".join(str(part) for part in parts)
    ctx.run(args, pty=platform.system() != "Windows", echo=True)


def optional(ctx, *parts):
    if shutil.which(parts[0]):
        run(ctx, *parts)
    else:
        print(f"Executable '{parts[0]}' not found, skipping")


def touch(path: Path):
    with open(path, "w"):
        pass


def download_rcc(system: Optional[str] = None) -> Path:
    if system is None:
        system = platform.system()

    rcc_url = RCC_URLS[system]
    rcc_path = BIN / "rcc.exe" if system == "Windows" else BIN / "rcc"

    print(f"Downloading '{rcc_url}' to '{rcc_path}'")
    urllib.request.urlretrieve(rcc_url, rcc_path)
    st = os.stat(rcc_path)
    os.chmod(rcc_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return rcc_path


def copy_templates():
    src = CURDIR / ".." / "templates"
    print(f"Copying templates '{src}' to '{TEMPLATES}'")
    shutil.copytree(src, TEMPLATES, dirs_exist_ok=True)


def go_build(ctx, output: Path, system: Optional[str] = None, arch = "amd64"):
    if system is None:
        system = platform.system()

    with open(CURDIR / "VERSION") as fd:
        version = fd.read().strip()

    output.mkdir(parents=True, exist_ok=True)
    exe = "robo.exe" if system == "Windows" else "robo"

    with environ({"GOOS": system.lower(), "GOARCH": arch}):
        run(
            ctx,
            "go",
            "build",
            "-ldflags",
            f'"-X github.com/robocorp/robo/cli/cmd.version={version} -w -s"',
            "-o",
            output / exe,
            CURDIR,
        )


@contextmanager
def environ(overrides: dict[str, str]):
    before = dict(os.environ)
    try:
        os.environ.update(overrides)
        yield
    finally:
        os.environ = before


@task
def clean(ctx):
    TIMESTAMP.unlink(missing_ok=True)

    if BUILD.exists():
        print("Removing build artifacts:", BUILD)
        shutil.rmtree(BUILD)

    for path in chain(BIN.glob("*"), TEMPLATES.glob("*")):
        if path.suffix == ".go" or path.name == ".gitignore":
            continue

        print("Removing include:", path)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

@task
def lint(ctx):
    """Run static analysis"""
    run(ctx, "go", "vet", CURDIR)
    optional(ctx, "golangci-lint", "run", CURDIR)


@task
def pretty(ctx):
    """Auto-format code"""
    run(ctx, "gofmt", "-s", "-w", CURDIR)
    optional(ctx, "golines", "-m", 88, "-w", CURDIR)
    optional(ctx, "goimports", "-w", CURDIR)


@task
def test(ctx):
    """Run unittests"""
    run(ctx, "go", "test", "-coverpkg=./...", "./...")


@task
def prepare(ctx):
    """Download/copy static assets"""
    download_rcc()
    copy_templates()
    touch(TIMESTAMP)


@task
def build(ctx):
    """Build robo binary"""
    if not TIMESTAMP.exists():
        print("Pre-requisites not met, run 'invoke prepare'")
        sys.exit(1)

    go_build(ctx, BUILD)


@task(clean)
def crossbuild(ctx):
    """Build for all platforms"""
    copy_templates()

    for arch, system, dirname in (
        ("amd64", "Windows", "windows64"),
        ("amd64", "Linux", "linux64"),
        ("amd64", "Darwin", "macos64"),
    ):
            rcc = download_rcc(system)
            go_build(ctx, output=BUILD / dirname, system=system, arch=arch)
            rcc.unlink()


@task
def macos_sign(ctx):
    """Sign binary for macOS"""
    assert platform.system() == "Darwin"
    cert_data = os.environ["MACOS_SIGNING_CERT"]
    cert_password = os.environ["MACOS_SIGNING_CERT_PASSWORD"]

    try:
        ctx.run(f"xcrun security create-keychain -p {cert_password} build.keychain")
        ctx.run("xcrun security default-keychain -s build.keychain")
        ctx.run(f"xcrun security unlock-keychain -p {cert_password} build.keychain")
        ctx.run(f"echo {cert_data}| base64 --decode -o cert.p12")
        ctx.run(f"xcrun security import cert.p12 -A -P {cert_password}")
        ctx.run(
            f"xcrun security set-key-partition-list -S apple-tool:,apple: -s -k {cert_password} build.keychain"
        )
        ctx.run(
            'xcrun codesign --entitlements entitlements.mac.plist --deep -o runtime -s "Robocorp Technologies, Inc." --timestamp build/macos64/robo'
        )
    finally:
        Path("cert.p12").unlink()


@task
def macos_notarize(ctx):
    """Notarize binary for macOS"""
    assert platform.system() == "Darwin"
    apple_id = os.environ["MACOS_APP_ID_FOR_SIGNING"]
    signing_password = os.environ["MACOS_APP_ID_PASS_FOR_SIGNING"]

    ctx.run("zip robo.zip build/macos64/robo")
    ctx.run(
        f"xcrun notarytool submit robo.zip --apple-id {apple_id} --password {signing_password} --team-id 2H9N5J72C7 --wait"
    )
    # TODO: Staple notarization to binary
    ctx.run("mkdir -p dist")
    ctx.run("unzip robo.zip -d dist")
    ctx.run("ls dist/")
    ctx.run("ls dist/build")

def cask_template(version: str, sha256: str, url: str):
    return f"""cask "robo" do
  version "{version}"
  sha256 "{sha256}"

  # robocorp.com was verified as official when first introduced to the cask
  url "{url}"
  name "robo"
  desc "Tooling for managing and distributing self-contained automation robots"
  homepage "https://github.com/robocorp/rcc"

  binary "robo"
end
"""

@task
def macos_push_brew(ctx, filename: str, version: str):
    """Create artifact for brew cask """

    import hashlib
    with open(filename,"rb") as f:
        bytes = f.read() # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest();
        print(readable_hash)

    url = f"https://downloads.robocorp.com/robo/releases/{version}/macos64/robo"
    ruby_cask_file = cask_template(version, readable_hash, url)
    print(ruby_cask_file)

    with open("cask/Casks/robo.rb", "w") as f:
        f.write(ruby_cask_file)


    ctx.run("cd cask && git add -u")
    ctx.run(f'cd cask && git commit -m "robo updated to {version}"')
    ctx.run("cd cask && git push")
