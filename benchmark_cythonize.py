import pyximport

pyximport.install(pyimport=True, load_py_module_on_import_failure=True)

import benchmark

benchmark.main()
