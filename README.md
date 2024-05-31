> Note: As of May 2024, this repository has been archived and the development of the reference implementation for metadata extractors API continues under the [`datatractor/beam`](https://github.com/datatractor/beam) project.

<div align="center" style="padding-bottom: 1em;">
<img width="100px" align="center" src="https://avatars.githubusercontent.com/u/74017645?s=200&v=4">
</div>

# <div align="center">MaRDA Metadata Extractors: API</div>

<div align="center">


[![Documentation](https://badgen.net/badge/docs/marda-alliance.github.io/blue?icon=firefox)](https://marda-alliance.github.io/metadata_extractors_api)
![Github status](https://badgen.net/github/checks/marda-alliance/metadata_extractors_api/?icon=github)

</div>

A place for the [Metadata Extractors WG](https://github.com/marda-alliance/metadata_extractors/) to work on ideas regarding API development, wrapping existing codes and associated tools.

## `marda_extractors_api` package

There is a draft Python 3.10 package presented under the `./marda_extractors_api`
directory.
It has no non-optional dependencies and can be used to:
- query the [Extractors Registry](https://marda-registry.fly.dev/) for extractors that support a given file type,
- install those extractors in a fresh Python virtual environment environment via `pip`,
- invoke the extractor either in Python or at the CLI, producing Python objects or files on disk.

### Installation

```shell
git clone git@github.com:marda-alliance/metadata_extractors_api.git
cd metadata_extractors_api;
pip install .
```

### Usage

Currently, you can use the `extract` function from the `metadata_extractors_api` inside your own Python code:

```python
from marda_extractors_api import extract

# extract(<input_type>, <input_path>)
data = extract("./example.mpr",  "biologic-mpr")
```

This example will install the first compatible `biologic-mpr` extractor it finds in the registry into a fresh virtualenv, and then execute it on the file at `example.mpr`.

By default, the `extract` function will attempt to use the extractor's Python-based invocation (i.e. the optional `preferred_mode="python"` argument is specified). This means the extractor will be executed from within python, and the returned `data` object will be a Python object as defined (and supported) by the extractor. This may require additional packages to be installed, for examples `pandas` or `xarray`, which are both supported via the installation command `pip install .[formats]` above. If you encounter the following traceback, a missing "format" (such as `xarray` here) is the likely reason:

```
Traceback (most recent call last):
    [...]
    data = pickle.loads(shm.buf)
ModuleNotFoundError: No module named 'xarray'
```

Alternatively, if the `preferred_mode="cli"` argument is specified, the extractor will be executed using its command-line invocation. This means the output of the extractor will most likely be a file, which can be further specified using the `output_type` argument:

```python
from marda_extractors_api import extract
ret = extract("example.mpr", "biologic-mpr", output_path="output.nc", preferred_mode = "cli")
```

In this case, the `ret` will be empty bytes, and the output of the extractor should appear in the `output.nc` file.


### Plans

- [x] Isolation of extractor environments
    - By installing each extractor into a fresh virtualenv, multiple extractors
      can be installed with possibly complex (and non-Python) dependencies.
    - This could be achieved by Python virtualenvs or Docker containers (or
      both!).
    - This will involve setting up a system for checking locally which
      extractors are available on a given machine.
    - Returning Python objects in memory will be tricker in this case, and would
      probably require choosing a few "blessed" formats that can be passed
      across subprocesses without any extractor specific classes,
      e.g., raw JSON/Python dicts, pandas dataframes or xarray datasets (as
      optional requirements, by demand).
- [ ] A command-line for quickly running e.g., `marda-extract <filename>`
- [ ] Extractor scaffold/template/plugin
    - If it can be kept similarly low-dependency, this package could also
      implement an extractor scaffold for those who want to modify existing
      extractors to follow the MaRDA API, and could automatically generate the
      appropriate registry entries for them.
- [ ] Testing and validation
    - We would like to move towards output validation, and this package would be
      the natural place to do so, again, perhaps supporting a few blessed
      formats, e.g., validating JSON output against an extractor-provided JSONSchema.
    - A testing mode that runs an extractor against all example files in the
      registry for that file type.
- [ ] File type detection following any rules added to the schemas
- [ ] Support for parallel processing
    - This package could handle invoking the same extractor on a large number of files.
- [ ] Support for other installation methods, such as `conda` and `docker`, to
  expand beyond purely `pip`-installable extractors.
