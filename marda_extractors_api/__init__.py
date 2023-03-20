import subprocess
from enum import Enum
from pathlib import Path

import httpx

__all__ = ("extract", "MardaExtractor")

REGISTRY_BASE_URL = "https://marda-registry.fly.dev"


class SupportedExecutionMethod(Enum):
    CLI = "cli"
    PYTHON = "python"


def extract(
    file_path: Path,
    file_type: str,
    output_file: Path | None = None,
    preferred_mode: SupportedExecutionMethod = SupportedExecutionMethod.PYTHON,
):
    """Parse a file given its path and file type ID
    in the MaRDA registry.
    """

    if not file_path.exists():
        raise RuntimeError(f"File {file_path} does not exist")

    response = httpx.get(f"{REGISTRY_BASE_URL}/filetypes/{file_type}")
    if response.status_code != 200:
        raise RuntimeError(
            f"Could not find file type {file_type!r} in the registry at {response.url!r}"
        )
    extractors = response.json()["registered_extractors"]
    if not extractors:
        raise RuntimeError(
            f"No extractors found for file type {file_type!r} in the registry"
        )
    elif len(extractors) > 1:
        print(
            f"Discovered multiple extractors: {extractors}, using the first ({extractors[0]})"
        )

    extractor = extractors[0]
    entry = httpx.get(f"{REGISTRY_BASE_URL}/extractors/{extractor}")
    if response.status_code != 200:
        raise RuntimeError(f"Could not find extractor {extractor!r} in the registry")

    extractor = MardaExtractor(entry.json(), preferred_mode=preferred_mode)

    return extractor.execute(file_type, file_path, output_file)


class MardaExtractor:
    """A plan for parsing a file."""

    entry: dict
    """The registry entry to use for parsing."""

    def __init__(
        self,
        entry: dict,
        install: bool = False,
        preferred_mode: SupportedExecutionMethod = SupportedExecutionMethod.PYTHON,
    ):
        """Initialize the plan, optionally installing the specific parser package."""
        self.entry = entry
        self.preferred_mode = preferred_mode
        if install:
            self.install()

    def install(self):
        command = ["pip", "install", f"git+{self.entry['source_repository']}"]
        subprocess.check_output(command)

    def execute(self, file_type: str, file_path: Path, output_file: Path | None = None):
        if file_type not in [d["id"] for d in self.entry["supported_filetypes"]]:
            raise ValueError(
                f"File type {file_type!r} not supported by {self.entry['id']!r}"
            )

        if self.entry["id"] == "yadg":
            self.entry["usage"].append(
                "python:yadg.extractors.extract({{ file_type }}, {{ file_path }})"
            )

        method, command = self.parse_usage(
            self.entry["usage"], preferred_mode=self.preferred_mode
        )

        if output_file is None:
            output_file = file_path.with_suffix(".json")

        def apply_template_args(
            command, file_type: str, file_path: Path, output_file: Path | None = None
        ):
            if method == SupportedExecutionMethod.CLI:
                command = command.replace("{{ file_type }}", file_type)
                command = command.replace("{{ file_path }}", str(file_path))
                if output_file:
                    command = command.replace("{{ output_file }}", str(output_file))
            else:
                command = command.replace("{{ file_type }}", f"{str(file_type)!r}")
                command = command.replace("{{ file_path }}", f"{str(file_path)!r}")
                if output_file:
                    command = command.replace(
                        "{{ output_file }}", f"{str(output_file)!r}"
                    )

            return command

        command = apply_template_args(command, file_type, file_path, output_file)

        if method == SupportedExecutionMethod.CLI:
            output = self._execute_cli(command)
            if not output_file.exists():
                raise RuntimeError(f"Output file {output_file} does not exist")
            print(f"Wrote output to {output_file}")

        elif method == SupportedExecutionMethod.PYTHON:
            output = self._execute_python(command)

        return output

    def _execute_cli(self, command):
        return subprocess.check_output(command)

    def _execute_python(self, command):
        from importlib import import_module

        module = ".".join(command.split("(")[0].split(".")[0:-1])

        function = command.split("(")[0].split(".")[-1]
        extractor_module = import_module(module)
        # Treat contents of first brackets as arguments
        args = [
            d.strip().strip("'") for d in command.split("(")[1].split(")")[0].split(",")
        ]
        return getattr(extractor_module, function)(*args)

    @staticmethod
    def parse_usage(
        usage: list[str],
        preferred_mode: SupportedExecutionMethod = SupportedExecutionMethod.PYTHON,
    ) -> tuple[SupportedExecutionMethod, str]:
        """Parse e.g., 'cli: yadg extract {{ file_type }} {{ file_path }} {{ output_file }}'."""
        for usages in usage:
            method = SupportedExecutionMethod(usages.split(":")[0])
            command = "".join(usages.split(":")[1:])

            if method == preferred_mode:
                return method, command

        return method, command
