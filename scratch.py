"""Some noodling around from the first office hours session,
should be tidied and split up at some point...

"""
from functools import wraps
from pydantic import BaseModel
import os
from marda_schema import FileType, InputSchema, OutputSchema, Extractor
from marda_registry import search

class Parser(BaseModel):
    """A base model for parsers that:

    - Can be instantiated from the registry directly:

        ```python 
        # Get a list of all matching MPR parsers
        parsers = Parser.from_registry(filetype="MPR")
        ```

    - Can be made to use different runtime backends instead of native Python, e.g.,
    if the parser from the registry or elsewhere supports another backend, e.g., docker, `self.parse()`
    could simply call 
        - `sp.Popen("docker run my_extractor --filename mydata > my_output.json")`,
        where `my_extractor` is either a remote container in the MaRDA docker registry (i.e., a registry of 
        docker containers like docker hub) or a GitHub repo that contains a specified Dockerfile,
        - or a compiled extractor from the command-line, 
        - or a web API.

    - Can be used as a mixin for existing parser classes, providing the
    `.parse(filename)` entrypoint.

    """
    filename: str 
    multiprocess: bool = True
    file_type: FileType 
    # output_schema: OutputSchema
    
    @staticmethod
    def _filetype_from_registry(fts="biologic", registry_url="extractors.marda-alliance.org"):
        """fts over registry"""
        return search(fts)[0]

    @staticmethod
    def _extractor_from_registry(file_type: FileType):
        return search(file_type)[0]

    def parse(filename):
        if self.extractor.lang == "py":
            return self._parse_python(filename)
        else:
            return self._parse_cmdline(
                filename, **parser_and_runtime_args
            )

    def _parse_python(filename):
        return self.extractor(), output_schema

    def _parse_cmdline(filename):
        return subprocess.Popen(stdout), output_schema

parser = Parser.from_registry(FileType.biologic_mpr).parse(filename)


def marda_extractor(fn):
    """A decorator that takes any normal function and tries to accept some specified MaRDA inputs and
    coerces MaRDA outputs.

    """
    @wraps(fn)
    def wrapper(filename: os.PathLike):
        parser = Parser()
        parser.extractor = fn
        return parser.parse(filename), parser.output_schema


"""----- some existing package code called foo 

Instead of breaking their current API for the `read_mpr` function,
create another wrapper that itself will be wrapped by the `marda_extractor`
decorator.

"""

from .foo import read_mpr
"""e.g.,
```python
def read_mpr(/, file=None):
     return {"data": []}
```
noting the different format the `read_mpr` expects (argument is called file instead of filename)
"""

@marda_extractor
def read_mpr_marda(filename):
    return read_mpr(file=filename)

def read_mpr_as_csv(filename):
    """separate registry entry to the one above, as it then also converts to csv"""
    pandas.write_csv(read_mpr(filename))

    
"""---- registry on GitHub  --- """

registry = [
    Extractor(**{
        file_type: FileType 
        input_schema: InputSchema
        output_schema: OutputSchema
        source: "github.com/foo/foo",
        entrypoints: [
            "pypi:<foo>:foo.read_mpr_marda",
            "docker:docker.marda.org:foo",
            "dockerfile:https://github.com/foo/foo/blob/Dockerfile"
        ],
    })
]
