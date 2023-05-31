# MaRDA Extractors WG API Development

A place for the [Metadata Extractors WG](https://github.com/marda-alliance/metadata_extractors/) to work on ideas regarding API development, wrapping existing codes and associated tools.

## `marda_extractors_api` package

There is a draft Python 3.10 package presented under the `./marda_extractors_api`
directory.
It has no dependencies and can be used to:
- query the [Extractors Registry](https://marda-registry.fly.dev/) for extractors that support a given file type,
- install those extractors in the current environment via `pip`
- invoke the extractor either in Python or at the CLI, producing Python objects
  or files on disk.

### Installation

> **Warning**
> Ideally, you should install the package into a fresh virtualenv, as
attempting to extract from data files will currently lead to new packages being installed
in that environment.

```shell
git@github.com:marda-alliance/metadata_extractors_api.git
pip install .
```

### Usage

This example can be found in `scripts/biologic-mpr-example.py`.

```python
from marda_extractors_api import extract

# extract(<input_type>, <input_path>)
data = extract("example.mpr", "biologic-mpr")
```


### Plans

- [ ] Isolation of extractor environments
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
- [ ] File type detection following any rules added to the schemac
- [ ] A command-line for quickly running e.g., `marda-extract <filename>`
- [ ] Support for parallel processing
    - This package could handle invoking the same extractor on a large number of files.
