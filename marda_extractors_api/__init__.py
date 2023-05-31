import json
import subprocess
import urllib.request
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Callable

__all__ = ("extract", "MardaExtractor")

REGISTRY_BASE_URL = "https://marda-registry.fly.dev"


class SupportedExecutionMethod(Enum):
    CLI = "cli"
    PYTHON = "python"


def extract(
    file_path: Path | str,
    file_type: str,
    output_file: Path | str | None = None,
    preferred_mode: SupportedExecutionMethod = SupportedExecutionMethod.PYTHON,
):
    """Parse a file given its path and file type ID
    in the MaRDA registry.
    """

    file_path = Path(file_path)
    if not file_path.exists():
        raise RuntimeError(f"File {file_path} does not exist")

    output_file = Path(output_file) if output_file else None

    response = urllib.request.urlopen(f"{REGISTRY_BASE_URL}/filetypes/{file_type}")
    if response.status != 200:
        raise RuntimeError(
            f"Could not find file type {file_type!r} in the registry at {response.url!r}"
        )
    json_response = json.loads(response.read().decode("utf-8"))
    extractors = json_response["registered_extractors"]
    if not extractors:
        raise RuntimeError(
            f"No extractors found for file type {file_type!r} in the registry"
        )
    elif len(extractors) > 1:
        print(
            f"Discovered multiple extractors: {extractors}, using the first ({extractors[0]})"
        )

    extractor = extractors[0]
    entry = urllib.request.urlopen(f"{REGISTRY_BASE_URL}/extractors/{extractor}")
    if response.status != 200:
        raise RuntimeError(f"Could not find extractor {extractor!r} in the registry")

    entry_json = json.loads(entry.read().decode("utf-8"))

    extractor = MardaExtractor(entry_json, preferred_mode=preferred_mode)

    return extractor.execute(file_type, file_path, output_file)


class MardaExtractor:
    """A plan for parsing a file."""

    entry: dict
    """The registry entry to use for parsing."""

    def __init__(
        self,
        entry: dict,
        install: bool = True,
        preferred_mode: SupportedExecutionMethod = SupportedExecutionMethod.PYTHON,
    ):
        """Initialize the plan, optionally installing the specific parser package."""
        self.entry = entry
        self.preferred_mode = preferred_mode
        if install:
            self.install()

    def install(self):
        print(f"Attempting to install {self.entry['id']}")
        for instructions in self.entry["installation"]:
            if instructions["method"] == "pip":
                try:
                    for p in instructions["packages"]:
                        command = ["pip", "install", f"{p}"]
                        subprocess.run(command, check=True)
                    break
                except Exception:
                    continue

    def execute(
        self,
        file_type: str,
        file_path: Path,
        output_file: Path | None = None,
    ):
        if file_type not in {_["id"] for _ in self.entry["supported_filetypes"]}:
            raise ValueError(
                f"File type {file_type!r} not supported by {self.entry['id']!r}"
            )

        method, command, setup = self.parse_usage(
            self.entry["usage"], preferred_mode=self.preferred_mode
        )

        if output_file is None:
            output_file = file_path.with_suffix(".json")

        command = self.apply_template_args(
            command, method, file_type, file_path, output_file
        )

        if method == SupportedExecutionMethod.CLI:
            output = self._execute_cli(command)
            if not output_file.exists():
                raise RuntimeError(f"Output file {output_file} does not exist")
            print(f"Wrote output to {output_file}")

        elif method == SupportedExecutionMethod.PYTHON:
            output = self._execute_python(command, setup)

        return output

    def _execute_cli(self, command):
        print(f"Exexcuting {command}")
        return subprocess.run(
            command.split(),
            check=False,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )

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
        file_type: str,
        file_path: Path,
        output_file: Path | None = None,
    ):
        if method == SupportedExecutionMethod.CLI:
            command = command.replace("{{ input_type }}", f"marda:{file_type}")
            command = command.replace("{{ input_path }}", str(file_path))
            if output_file:
                command = command.replace("{{ output_path }}", str(output_file))
        else:
            command = command.replace("{{ input_type }}", f"{str(file_type)!r}")
            command = command.replace("{{ input_path }}", f"{str(file_path)!r}")
            if output_file:
                command = command.replace("{{ output_path }}", f"{str(output_file)!r}")

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
