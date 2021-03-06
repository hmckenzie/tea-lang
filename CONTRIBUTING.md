## FILES

## How do I use Tea?
Make sure that you have Python 3.7, pip (for Python 3.7), and pipenv (for Python 3.7) installed. 
Start a pipenv: `pipenv shell`
From inside your environment, download all dependencies from Pipfile (`pipenv update`). This will take awhile because it builds Z3.
Add Tea to your Python path by creating `.env` file that has the following one-liner in it: `PYTHONPATH=${PYTHONPATH}:${PWD}`
To run tests and see output, run: `pytest tests/integration_tests/test_integration.py -s`

The main code base is written in Python and lives in the `tea` directory. The `tests` directory is used for developing and debugging and uses datasets in the `datasets` directory. Not all the datasets used in `tests/test_tea.py` are included in the `datasets` repository. 
`tea/solver.py` contains the constraint solving module for both tests -> properties and properties -> tests.
`tea/ast.py` implements Tea's Abstract Syntax Tree (AST). 
`tea/build.py` builds up Tea's AST for programs.
`tea/dataset.py` contains a runtime data structure that represents and contains the data the user provides. 
`tea/evaluate.py` is the main interpreter file.
`tea/evaluate_helper_methods.py` contains the helper methods for `evaluate.py`.
`tea/evaluate_data_structures.py` contains the data structuers used in `evaluate.py` and `evaluate_helper_methods.py`.
`tea/errors.py` is empty. It will contain some code for providing helpful error messages.

**All of the above are still changing!**