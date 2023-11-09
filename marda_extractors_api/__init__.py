import json
import multiprocessing.managers
import multiprocessing.shared_memory
import pickle
import platform
import re
import subprocess
import urllib.request
import venv
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Optional

__all__ = ("extract", "MardaExtractor")

REGISTRY_BASE_URL = "https://marda-registry.fly.dev"
BIN = "Scripts" if platform.system() == "Windows" else "bin"


class SupportedExecutionMethod(Enum):
    # TODO: would be nice to generate these directly from the LinkML schema
    CLI = "cli"
    PYTHON = "python"


class SupportedInstallationMethod(Enum):
    PIP = "pip"
    CONDA = "conda"


def extract(
    input_path: Path | str,
    input_type: str,
    output_path: Path | str | None = None,
    output_type: str | None = None,
    preferred_mode: SupportedExecutionMethod | str = SupportedExecutionMethod.PYTHON,
    install: bool = True,
    use_venv: bool = True,
) -> Any:
    """Parse a file given its path and file type ID
    in the MaRDA registry.

    Parameters:
        input_path: The path or URL of the file to parse.
        input_type: The ID of the file type in the MaRDA registry.
        output_path: The path to write the output to.
            If not provided, the output will be requested to be written
            to a file with the same name as the input file, but with a .json extension.
        output_type: A string specifying the desired output type.
        preferred_mode: The preferred execution method.
            If the extractor supports both Python and CLI, this will be used to determine
            which to use. If the extractor only supports one method, this will be ignored.
            Accepts the `SupportedExecutionMethod` values of "cli" or "python".
        install: Whether to install the extractor package before running it. Defaults to True.

    Returns:
        The output of the extractor, either a Python object or nothing.

    """
    tmp_path: Optional[Path] = None
    try:
        if isinstance(input_path, str) and re.match("^http[s]://*", input_path):
            _tmp_path, _ = urllib.request.urlretrieve(input_path)
            tmp_path = Path(_tmp_path)
            input_path = tmp_path

        input_path = Path(input_path)

        if not input_path.exists():
            raise RuntimeError(f"File {input_path} does not exist")

        output_path = Path(output_path) if output_path else None

        if isinstance(preferred_mode, str):
            preferred_mode = SupportedExecutionMethod(preferred_mode)

        response = urllib.request.urlopen(f"{REGISTRY_BASE_URL}/filetypes/{input_type}")
        if response.status != 200:
            raise RuntimeError(
                f"Could not find file type {input_type!r} in the registry at {response.url!r}"
            )
        json_response = json.loads(response.read().decode("utf-8"))
        extractors = json_response["registered_extractors"]
        if not extractors:
            raise RuntimeError(
                f"No extractors found for file type {input_type!r} in the registry"
            )
        elif len(extractors) > 1:
            print(
                f"Discovered multiple extractors: {extractors}, using the first ({extractors[0]})"
            )

        extractor = extractors[0]
        entry = urllib.request.urlopen(f"{REGISTRY_BASE_URL}/extractors/{extractor}")
        if response.status != 200:
            raise RuntimeError(
                f"Could not find extractor {extractor!r} in the registry"
            )

        entry_json = json.loads(entry.read().decode("utf-8"))

        extractor = MardaExtractor(
            entry_json,
            preferred_mode=preferred_mode,
            install=install,
            use_venv=use_venv,
        )

        return extractor.execute(
            input_type=input_type,
            input_path=input_path,
            output_type=output_type,
            output_path=output_path,
        )
    finally:
        if tmp_path:
            tmp_path.unlink()


class MardaExtractor:
    """A plan for parsing a file."""

    entry: dict
    """The registry entry to use for parsing."""

    def __init__(
        self,
        entry: dict,
        install: bool = True,
        preferred_mode: SupportedExecutionMethod = SupportedExecutionMethod.PYTHON,
        use_venv: bool = True,
    ):
        """Initialize the plan, optionally installing the specific parser package."""
        self.entry = entry
        self.preferred_mode = preferred_mode

        if use_venv:
            self.venv_dir: Path | None = (
                Path(__file__).parent.parent / "marda-venvs" / f"env-{self.entry['id']}"
            )
            venv.create(self.venv_dir, with_pip=True)
        else:
            self.venv_dir = None

        if install:
            self.install()

    def install(self):
        """Follows the `pip` installation instructions for the entry inside
        the configured venv.

        """
        print(f"Attempting to install {self.entry['id']}")
        for instructions in self.entry["installation"]:
            method = SupportedInstallationMethod(instructions["method"])
            if method == SupportedInstallationMethod.PIP:
                try:
                    for p in instructions["packages"]:
                        command = [
                            str(self.venv_dir / BIN / "python")
                            if self.venv_dir
                            else "python",
                            "-m",
                            "pip",
                            "install",
                            f"{p}",
                        ]
                        subprocess.run(command, check=True)
                    break
                except Exception:
                    continue
            else:
                raise RuntimeError(
                    f"Installation method {instructions['method']} not yet supported"
                )

    def execute(
        self,
        input_type: str,
        input_path: Path,
        output_type: str | None = None,
        output_path: Path | None = None,
    ):
        if input_type not in {_["id"] for _ in self.entry["supported_filetypes"]}:
            raise ValueError(
                f"File type {input_type!r} not supported by {self.entry['id']!r}"
            )

        method, command, setup = self.parse_usage(
            self.entry["usage"], preferred_mode=self.preferred_mode
        )

        if output_path is None:
            output_path = input_path.with_suffix(".json")

        command = self.apply_template_args(
            command,
            method,
            input_type=input_type,
            input_path=input_path,
            output_type=output_type,
            output_path=output_path,
        )

        if setup is not None:
            setup = self.apply_template_args(
                setup,
                method,
                input_type=input_type,
                input_path=input_path,
                output_type=output_type,
                output_path=output_path,
            )

        if method == SupportedExecutionMethod.CLI:
            print(f"Executing {command}")
            if self.venv_dir:
                venv_bin_command = str(self.venv_dir / BIN / command)
                output = self._execute_cli_venv(venv_bin_command)
            else:
                output = self._execute_cli(command)

            if not output_path.exists():
                raise RuntimeError(
                    f"Requested output file {output_path} does not exist"
                )

            print(f"Wrote output to {output_path}")

        elif method == SupportedExecutionMethod.PYTHON:
            if self.venv_dir:
                output = self._execute_python_venv(command, setup)
            else:
                output = self._execute_python(command, setup)

        return output

    def _execute_cli(self, command):
        print(f"Executing {command=}")
        results = subprocess.check_output(command, shell=True)
        return results

    def _execute_cli_venv(self, command):
        print(f"Executing {command=} in venv")
        py_cmd = f"import subprocess; subprocess.check_output(r'{command}', shell=True)"
        command = [str(self.venv_dir / BIN / "python"), "-c", py_cmd]
        results = subprocess.check_output(command)
        return results

    @staticmethod
    def _prepare_python(command) -> tuple[list[str], list[str], dict]:
        function_tree = command.split("(")[0].split(".")
        # Treat contents of first brackets as arguments
        # TODO: this gets a bit gross with more complex arguments with nested brackets.
        # This parser will need to be made very robust

        segments = command.split("(")[1].split(")")[0].split(",")
        kwargs = {}
        args = []

        def dequote(s: str):
            s = s.strip()
            if s.startswith("'") or s.endswith("'"):
                s = s.removeprefix("'")
                s = s.removesuffix("'")
            elif s.startswith('"') or s.endswith('"'):
                s = s.removeprefix('"')
                s = s.removesuffix('"')
            return s.strip()

        def _parse_python_arg(arg: str):
            if "=" in arg:
                split_arg = arg.split("=")
                if len(split_arg) > 2 or "{" in arg or "}" in arg:
                    raise RuntimeError(f"Cannot parse {arg}")

                return {dequote(arg.split("=")[0]): dequote(arg.split("=")[1])}
            else:
                return dequote(arg)

        for arg in segments:
            parsed_arg = _parse_python_arg(arg)
            if isinstance(parsed_arg, dict):
                kwargs.update(parsed_arg)
            else:
                args.append(parsed_arg)

        return function_tree, args, kwargs

    def _execute_python_venv(self, entry_command: str, setup: str):
        data = None

        with multiprocessing.managers.SharedMemoryManager() as shmm:
            shm = shmm.SharedMemory(size=1024 * 1024 * 1024)
            py_cmd = (
                f'print("Launching extractor"); import {setup}; import pickle; import multiprocessing.shared_memory;'
                + f"shm = multiprocessing.shared_memory.SharedMemory(name={shm.name!r});"
                + f"data = pickle.dumps({entry_command}); shm.buf[:len(data)] = data; print('Done!');"
            )

            if not self.venv_dir:
                raise RuntimeError("Something has gone wrong; no `venv_dir` set")

            command = [str(self.venv_dir / BIN / "python"), "-c", py_cmd]
            subprocess.check_output(
                command,
            )
            data = pickle.loads(shm.buf)

        return data

    def _execute_python(self, command: str, setup: str):
        from importlib import import_module

        if " " not in setup:
            module = setup
        else:
            raise RuntimeError("Only simple `import <setup>` invocation is supported")

        extractor_module = import_module(module)

        function_tree, args, kwargs = self._prepare_python(command)

        def _descend_function_tree(module: ModuleType, tree: list[str]) -> Callable:
            if tree[0] != module.__name__:
                raise RuntimeError(
                    "Module name mismatch: {module.__name__} != {tree[0]}"
                )
            _tree = tree.copy()
            _tree.pop(0)
            function: Callable | ModuleType = module
            while _tree:
                function = getattr(function, _tree.pop(0))
            return function  # type: ignore

        try:
            function = _descend_function_tree(extractor_module, function_tree)
        except AttributeError:
            raise RuntimeError(f"Could not resolve {function_tree} in {module}")

        return function(*args, **kwargs)

    @staticmethod
    def apply_template_args(
        command: str,
        method: SupportedExecutionMethod,
        input_type: str,
        input_path: Path,
        output_type: str | None = None,
        output_path: Path | None = None,
    ):
        if method == SupportedExecutionMethod.CLI:
            command = command.replace("{{ input_type }}", f"marda:{input_type}")
            command = command.replace("{{ input_path }}", str(input_path))
            if output_path:
                command = command.replace("{{ output_path }}", str(output_path))
            if output_type:
                command = command.replace("{{ output_type }}", str(output_type))
        else:
            command = command.replace("{{ input_type }}", f"{str(input_type)!r}")
            command = command.replace("{{ input_path }}", f"{str(input_path)!r}")
            if output_path:
                command = command.replace("{{ output_path }}", f"{str(output_path)!r}")
            if output_type:
                command = command.replace("{{ output_type }}", f"{str(output_type)!r}")

        return command

    @staticmethod
    def parse_usage(
        usage: list[dict],
        preferred_mode: SupportedExecutionMethod = SupportedExecutionMethod.PYTHON,
    ) -> tuple[SupportedExecutionMethod, str, str]:
        for usages in usage:
            method = SupportedExecutionMethod(usages["method"])
            command = usages["command"]
            setup = usages["setup"]

            if method == preferred_mode:
                return method, command, setup

        return method, command, setup
