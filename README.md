<div align="center" style="padding-bottom: 1em;">
<img width="100px" align="center" src="https://avatars.githubusercontent.com/u/74017645?s=200&v=4">
</div>

# <div align="center">MaRDA Metadata Extractors: API</div>
<div align="center">

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

You can use the metadata extractors inside your own Python code, or via the command-line:


```python
from marda_extractors_api import extract

# extract(<input_type>, <input_path>)
data = extract("./example.mpr",  "biologic-mpr")
```

This example will install the first compatible `biologic-mpr` extractor it finds in the registry into a fresh virtualenv, and then execute it on the file at `example.mpr`, requesting that the output is written to `./example.nc`.

The data returned will be a Python object that the extractor supports; this may require additional packages to be installed, for examples `pandas` or `xarray`, which are both supported via the installation command `pip install .[formats]` above.


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
- [x] A command-line for quickly running e.g., `marda-extract <filename>`
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
- [ ] Support for parallel processing
    - This package could handle invoking the same extractor on a large number of files.
- [ ] Support for other installation methods, such as `conda` and `docker`, to
  expand beyond purely `pip`-installable extractors.
