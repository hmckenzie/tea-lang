import attr

from .build import (load_data, load_data_from_url, const,
                    ordinal, isordinal,
                    nominal, isnominal,
                    ratio, isratio,
                    interval, isinterval, isnumeric,
                    select, compare, relate, predict,
                    get_var_from_list
                    )
from .evaluate import evaluate
import tea.helpers
import tea.runtimeDataStructures
import tea.z3_solver
from tea.z3_solver.solver import set_mode

from tea.runtimeDataStructures.dataset import Dataset
from tea.runtimeDataStructures.variable import AbstractVariable, NominalVariable, OrdinalVariable, NumericVariable
from tea.runtimeDataStructures.design import AbstractDesign, ObservationalDesign, ExperimentDesign

from typing import Dict
from .global_vals import *
from pathlib import Path


# Set at start of programs
# Used across functions
dataset_path = ''
dataset_obj = None
dataset_id = None
vars_objs = []
study_design = None

# For variables dictionary
var_name = 'name'
var_dtype = 'data type'
var_categories = 'categories'
var_drange = 'range'

# Assumptions
# Stats properties
assumptions = {}
alpha = 0.01

all_results = {}  # Used for multiple comparison correction

# For solver
MODE = 'strict'


# For testing purposes
def download_data(url, file_name):
    return load_data_from_url(url, file_name)


# @sets global dataset_path and dataaset_obj (of type Dataset)
def data_old(file, key=None):
    global dataset_path, dataset_obj, dataset_id

    # Require that the path to the data must be a string or a Path object
    assert (isinstance(file, str) or isinstance(file, Path))
    dataset_path = file
    dataset_id = key


def data(file, key=None): 
    return Dataset(file)

def define_variables_old(vars: Dict[str, str]):
    global vars_objs

    # reset the variables
    vars_objs = []

    for var in vars:
        name = var['name']

        if (var[var_dtype] == 'nominal'):
            categories = var[var_categories]
            v_obj = nominal(name, categories)
        elif (var[var_dtype] == 'ordinal'):
            categories = var[var_categories]
            v_obj = ordinal(name, categories)
        elif (var[var_dtype] == 'interval'):
            drange = None
            if var_drange in var:
                drange = var[var_drange]
            v_obj = interval(name, drange)
        else:
            assert (var[var_dtype] == 'ratio')
            drange = var[var_drange] if var_drange in var else None
            v_obj = interval(name, drange)

        vars_objs.append(v_obj)

def define_variables(vars: Dict[str, str]): 
    # List of Variables 
    variables = []

    for var in vars: 
        var_obj = AbstractVariable.create(var)
        variables.append(var_obj)
    
    return variables

def define_study_design_old(design: Dict[str, str]):
    global study_design, dataset_id, uid, alpha
    global btw_subj, within_subj

    # Check that variables are only assigned EITHER between OR within but NOT BOTH: 
    btw_vars = design[btw_subj] if btw_subj in design else None
    within_vars = design[within_subj] if within_subj in design else None

    if btw_vars:
        for b in btw_vars:
            if within_vars:
                for w in within_vars:
                    if b == w:
                        raise ValueError(
                            f"{b} CANNOT be a between subjects variable AND a within subjects variable. Can only be one or the other.")

    study_design = design

    # dataset_id = design[uid] if uid in design else None

def define_study_design(design: Dict[str, str], variables: list): 
    design_obj = AbstractDesign.create(design, variables)
    
    return design_obj


def assume(user_assumptions: Dict[str, str], mode=None):
    global alpha, alpha_keywords
    global assumptions
    global MODE

    if alpha_keywords[0] in user_assumptions:
        if alpha_keywords[1] in user_assumptions:
            assert (float(user_assumptions[alpha_keywords[0]]) == float(user_assumptions[alpha_keywords[1]]))

    for keyword in alpha_keywords:
        if keyword in user_assumptions:
            alpha = float(user_assumptions[keyword])

    assumptions = user_assumptions
    assumptions[alpha_keywords[1]] = alpha

    # Set MODE for dealing with assumptions
    if mode and mode == 'relaxed':
        MODE = mode
        log(f"\nRunning under {MODE.upper()} mode.\n")
        log(
            f"This means that user assertions will be checked. Should they fail, Tea will issue a warning but proceed as if user's assertions were true.")
    else:
        assert (mode == None or mode == 'strict')
        MODE = 'strict'
        log(f"\nRunning under {MODE.upper()} mode.\n")
        log(f"This means that user assertions will be checked. Should they fail, Tea will override user assertions.\n")


def hypothesize(vars: list, prediction: list = None):
    global dataset_path, vars_objs, study_design, dataset_obj, dataset_id
    global assumptions, all_results
    global MODE

    assert (dataset_path)
    assert (vars_objs)
    assert (study_design)

    dataset_obj = load_data(dataset_path, vars_objs, dataset_id)

    v_objs = []
    for v in vars:
        v_objs.append(get_var_from_list(v, vars_objs))  # may want to use Dataset instance method instead

    # Create and get back handle to AST node
    relationship = relate(v_objs, prediction)
    num_predictions = len(relationship.predictions) # use for multiple comparison correction

    # Interpret AST node, Returns ResultData object <-- this may need to change
    set_mode(MODE)
    num_comparisons = 1
    result = evaluate(dataset_obj, relationship, assumptions, study_design)

    # Make multiple comparison correction
    result.bonferroni_correction(num_comparisons)
    
    print(f"\n{result}")
    return result

    # Use assumptions and hypotheses for interpretation/reporting back to user
    # Make result human_readable
    # output = translate(result)

    # Give user output
    # return output

# TODO change how the key is input. Maybe we want to move this to the variables block
def tea_time(data, variables, design, assumptions=None, hypothesis=None, key=None): 
    tea_obj = Tea(variables, design, assumptions, hypothesis)
    tea_obj.load_data(data, key)


# TODO: This is a wrapper around the other API calls.
# Public facing Tea object end-user can construct 
class Tea(object): 
    def __init__(self, variables: Dict[str, str], design: Dict[str, str], assumptions=None, hypothesis=None): 
        self.variables = self.define_variables(variables)
        self.design = self.define_study_design(design, self.variables)

    def load_data(self, file, key=None): 
        self.data = Dataset(file)

        return self.data

    def define_variables(self, vars: Dict[str, str]): 
        # List of Variables 
        variables = []

        for var in vars: 
            var_obj = AbstractVariable.create(var)
            variables.append(var_obj)
        
        return variables
    
    def define_study_design(self, design: Dict[str, str], variables: list): 
        design_obj = AbstractDesign.create(design, variables)
    
        return design_obj

    def hypothesize(self, hypothesis): 
        pass