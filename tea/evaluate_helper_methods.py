from .global_vals import *
from .ast import *
from .dataset import Dataset
from .evaluate_data_structures import VarData, CombinedData, BivariateData, MultivariateData, ResData
from .solver import Tests, Assumptions

import attr
from typing import Any, Dict, List
from types import SimpleNamespace # allows for dot notation access for dictionaries
import copy

from scipy import stats # Stats library used
import statsmodels.api as sm
import statsmodels.formula.api as smf
# import numpy as np # Use some stats from numpy instead
import pandas as pd
import bootstrapped as bs


def determine_study_type(vars_data: list, design: Dict[str, str]):
    if design: 
        # Is the study type explicit? If so...
        if (study_type_identifier in design):
            # Is this study an experiment?
            if (design[study_type_identifier] == experiment_identifier):
                return experiment_identifier
            # Is this study an observational study?
            elif (design[study_type_identifier] == observational_identifier):
                return observational_identifier
            # We don't know what kind of study this is.
            else: 
                raise ValueError(f"Type of study is not supported:{design[study_type_identifier]}. Is it an experiment or an observational study?")
        # The study type is not explicit, so let's check the other properties...
        else: 
            # This might be an experiment.
            if (iv_identifier in design and dv_identifier in design): # dv_identifier??
                return experiment_identifier
            elif (contributor_identifier in design and outcome_identifier in design):
                return observational_identifier
            # We don't know what kind of study this is.
            else: 
                raise ValueError(f"Type of study is not supported:{design}. Is it an experiment or an observational study?") 
        


# @returns list of VarData objects with same info as @param vars but with one updated role characteristic
def assign_roles(vars_data: list, study_type: str, design: Dict[str, str]):
    vars = copy.deepcopy(vars_data)

    if study_type == experiment_identifier:
        ivs = design[iv_identifier] if isinstance(design[iv_identifier], list) else [design[iv_identifier]]
        dvs = design[dv_identifier] if isinstance(design[dv_identifier], list) else [design[dv_identifier]]

        for v in vars:
            if v.metadata[name] in ivs:
                setattr(v, 'role', iv_identifier)
            elif v.metadata[name] in dvs: 
                setattr(v, 'role', dv_identifier)
            else: 
                setattr(v, 'role', null_identifier) ## may need to be the covariates
    elif study_type == observational_identifier:
        contributors = design[contributor_identifier] if isinstance(design[contributor_identifier], list) else [design[contributor_identifier]]
        outcomes = design[outcome_identifier] if isinstance(design[outcome_identifier], list) else [design[outcome_identifier]]

        for v in vars: 
            if v.metadata[name] in contributors:
                setattr(v, 'role', contributor_identifier)
            elif v.metadata[name] in outcomes: 
                setattr(v, 'role', outcome_identifier)
            else: 
                setattr(v, 'role', null_identifier) ## may need to change

            # We don't know what kind of study this is.
    else: 
        raise ValueError(f"Type of study is not supported:{design[study_type_identifier]}. Is it an experiment or an observational study?")
    
    return vars

# Helper methods for Interpreter (in evaluate.py)
# Compute properties about the VarData objects in @param vars using data in @param dataset
def compute_data_properties(dataset, vars_data: list):
    vars = copy.deepcopy(vars_data)

    for v in vars:
        v.properties[sample_size] = len(dataset.select(v.metadata[name]))
        if v.is_continuous(): 
            v.properties[distribution] = compute_distribution(dataset.select(v.metadata[name]))
            v.properties[variance] = compute_variance(dataset.select(v.metadata[name]))
        elif v.is_categorical(): 
            v.properties[num_categories] = len(v.metadata[categories])

            # For each group (where DV is continuous) is the data normal?

        else: 
            raise ValueError (f"Not supported data type: {v.metadata[data_type]}")

    return vars

# Add equal variance property to @param combined_data
def add_eq_variance_property(dataset, combined_data: CombinedData, study_type: str): 
    xs = None
    ys = None
    cat_xs = []
    cont_ys = []
    grouped_data = []

    if study_type == experiment_identifier: 
        # Just need one variable to be Catogrical and another to be Continuous (regardless of role) -- both could be variable_identifier types
        xs = combined_data.get_vars(iv_identifier) 
        ys = combined_data.get_vars(dv_identifier) 
        
    else: # study_type == observational_identifier
        xs = combined_data.get_vars(contributor_identifier)
        ys = combined_data.get_vars(outcome_identifier)
    
    for x in xs: 
        if x.is_categorical(): 
            cat_xs.append(x)
    
    for y in ys: 
        if y.is_continuous(): 
            cont_ys.append(y)
    
    combined_data.properties[eq_variance] = None

    if cat_xs and cont_ys: 
        for y in ys:
            for x in xs: 
                cat = [k for k,v in x.metadata[categories].items()]
                for c in cat: 
                    data = dataset.select(y.metadata[name], where=[f"{x.metadata[name]} == '{c}'"])
                    grouped_data.append(data)
                if isinstance(combined_data, BivariateData):
                    # Equal variance
                    eq_var = compute_eq_variance(grouped_data)
                    combined_data.properties[eq_variance] = eq_var
                elif isinstance(combined_data, MultivariateData):
                    combined_data.properties[eq_variance + '::' + x.metadata[name] + ':' + y.metadata[name]] = compute_eq_variance(grouped_data)
                else: 
                    raise ValueError(f"combined_data_data object is neither BivariateData nor MultivariateData: {type(combined_data)}")

# Independent vs. Paired?
def add_paired_property(dataset, combined_data: CombinedData, study_type: str, design: Dict[str, str]=None): # check same sizes are identical
    global paired
    
    x = None
    y = None
    combined_data.properties[paired] = False
    if isinstance(combined_data, BivariateData): 
        if study_type == experiment_identifier: 
            # Just need one variable to be Categorical and another to be Continuous (regardless of role) 
            x = combined_data.get_vars(iv_identifier) 
            y = combined_data.get_vars(dv_identifier) 
            
        else: # study_type == observational_identifier
            x = combined_data.get_vars(contributor_identifier)
            y = combined_data.get_vars(outcome_identifier)
        
        if x and y:
            assert (len(x) == len(y) == 1)
            x = x[0]
            y = y[0]

            if x.is_categorical() and y.is_continuous(): 
                if within_subj in design and design[within_subj] == x.metadata[name]:
                    combined_data.properties[paired] = True

def add_categories_normal(dataset, combined_data: CombinedData, study_type: str, design: Dict[str, str]=None): 
    global cat_distribution

    xs = None
    ys = None
    cat_xs = []
    cont_ys = []
    grouped_data = dict()

    if study_type == experiment_identifier: 
        # Just need one variable to be Catogrical and another to be Continuous (regardless of role) -- both could be variable_identifier types
        xs = combined_data.get_vars(iv_identifier) 
        ys = combined_data.get_vars(dv_identifier) 
        
    else: # study_type == observational_identifier
        xs = combined_data.get_vars(contributor_identifier)
        ys = combined_data.get_vars(outcome_identifier)
    
    for x in xs: 
        if x.is_categorical(): 
            cat_xs.append(x)
    
    for y in ys: 
        if y.is_continuous(): 
            cont_ys.append(y)

    combined_data.properties[cat_distribution] = None

    if cat_xs and cont_ys: 
        for y in ys:
            for x in xs: 
                cat = [k for k,v in x.metadata[categories].items()]
                for c in cat: 
                    data = dataset.select(y.metadata[name], where=[f"{x.metadata[name]} == '{c}'"])
                    grouped_data_name =  str(x.metadata[name] + ':' + c)
                    grouped_data[grouped_data_name] = compute_distribution(data)
                combined_data.properties[cat_distribution] = dict()
                combined_data.properties[cat_distribution][y.metadata[name] + '::' + x.metadata[name]] = grouped_data

# Compute properties that are between/among VarData objects
def compute_combined_data_properties(dataset, combined_data: CombinedData, study_type: str, design: Dict[str, str]=None):
    assert (study_type == experiment_identifier or study_type == observational_identifier)
    combined = copy.deepcopy(combined_data)

    # Equal variance?
    add_eq_variance_property(dataset, combined, study_type)

    # Independent vs. Paired?
    add_paired_property(dataset, combined, study_type, design) # check sample sizes are identical

    # Add is_normal for every category? in dictionary
    add_categories_normal(dataset, combined, study_type, design)

    return combined

# Check normality of data
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.normaltest.html
# Based on D’Agostino, R. B. (1971), “An omnibus test of normality for moderate and large sample size”, Biometrika, 58, 341-348
# and D’Agostino, R. and Pearson, E. S. (1973), “Tests for departure from normality”, Biometrika, 60, 613-622
# Null hypothesis is that distribution comes from Normal Distribution
# Rejecting null means that distribution is NOT normal
def compute_distribution(data):
    norm_test = stats.normaltest(data, axis=0)
    # could just reutrn norm_test directly???
    return (norm_test[0], norm_test[1])
    # TODO: may want to compute/find the best distribution if not normal
 
# @returns bootstrapped variance for @param data
def compute_variance(data): 
    return -1

# Levene test to test for equal variances - Leven is more robust to nonnormal data than Bartlett's test
# Null Hypothesis is that samples have the same variances
# Rejecting null means that samples have different variances
# Default/currently using .05 alpha level
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.levene.html#scipy.stats.levene

def compute_eq_variance(groups_data):
    levene_test = stats.levene(*groups_data)
    return (levene_test[0], levene_test[1])

def is_normal(comp_data: CombinedData, alpha, data=None):
    if (data is not None): # raw data being checked for normality
        norm_test = compute_distribution(data)
        return (norm_test[1] < .05)
    else: 
        return comp_data.properties.dist[1] < alpha

def is_equal_variance(comp_data: CombinedData, alpha):
    return comp_data.properties.var[1] < alpha

def is_numeric(data_type: DataType):
    return data_type is DataType.INTERVAL or data_type is DataType.RATIO

def is_ordinal(data_type: DataType):
    return data_type is DataType.ORDINAL

def is_nominal(data_type: DataType):
    return data_type is DataType.NOMINAL

# TODO make more robust to variables that happen to be between/within -- random effects, not random effects, etc.
def is_independent_samples(var_name: str, design: Dict[str, str]):
    return var_name in design['between subjects'] if ('between subjects' in design) else False

def is_dependent_samples(var_name: str, design: Dict[str, str]):
    return var_name in design['within subjects'] if ('between subjects' in design) else False

# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html
# Possible parameters: a, b : array | axis (without, over entire arrays) | equal_var (default is True) | nan_policy (optional) 
def t_test_ind(iv: VarData, dv: VarData, predictions: list, comp_data: CombinedData, **kwargs):
    assert(len(comp_data.dataframes) == 2)
    assert(len(predictions) == 1)

    data = []
    for key, val in comp_data.dataframes.items():
        data.append(val)

    # What if we just return a lambda and all the test signatures are the same? That way, easy to swap out with constraint version?
    return stats.ttest_ind(data[0], data[1], equal_var=is_equal_variance(comp_data, kwargs['alpha']))

# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html
# Paramters: x, y : array_like | use_continuity (default=True, optional - for ties) | alternative (p-value for two-sided vs. one-sided)
# def utest(iv: VarData, dv: VarData, predictions: list, comp_data: CombinedData, **kwargs):
def utest(dataset, combined_data: BivariateData):
    import pdb; pdb.set_trace()
    assert (len(combined_data.vars) == 2)

    data = []
    for var in combined_data.vars:
        var_data = dataset.select(var.metadata[name], where=f"{var.metadata[query]}")
        data.append(var_data)

    return stats.mannwhitneyu(data[0], data[1], alternative='two-sided')

# https://docs.scipy.org/doc/scipy-0.18.1/reference/generated/scipy.stats.fisher_exact.html#scipy.stats.fisher_exact
# Parmaters: table (2 x 2) | alternative (default='two-sided' optional)
def fishers_exact(iv: VarData, dv: VarData, predictions: list, comp_data: CombinedData, **kwargs):
    assert(len(comp_data.dataframes) == 2)
    assert(len(predictions) == 1)

    data = []
    # calculate the 2 x 2 table 
    table = []
    stats.fisher_exact(table, alternative='two-sided')

# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_rel.html
# Parameters: a, b (array-like) | axis | nan_policy (default is 'propagate', optional)
def t_test_paired(iv: VarData, dv: VarData, predictions: list, comp_data: CombinedData, **kwargs):
    assert(len(comp_data.dataframes) == 2)
    assert(len(predictions) == 1)

    data = []
    for key, val in comp_data.dataframes.items():
        data.append(val)

    return stats.ttest_rel(data[0], data[1])

# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html
# Parameters: x (array-like) | y (array-like, optional) | zero_method (default = 'wilcox', optional) | correction (continuity correction, optional)
def wilcoxon_signed_rank(iv: VarData, dv: VarData, predictions: list, comp_data: CombinedData, **kwargs):
    assert(len(comp_data.dataframes) == 2)
    assert(len(predictions) == 1)

    data = []
    for key, val in comp_data.dataframes.items():
        # Use numbers for categories in ordinal data
        if (is_ordinal(dv.metadata['dtype'])):
            numeric = [dv.metadata['categories'][x] for x in val]
            val = numeric
        data.append(val)

    return stats.wilcoxon(data[0], data[1])

# https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.stats.pearsonr.html
# Parameters: x (array-like) | y (array-like)
def pearson_corr(iv: VarData, dv: VarData, predictions: list, comp_data: CombinedData, **kwargs):
    assert(len(comp_data.dataframes) == 2)

    data = []
    for key, val in comp_data.dataframes.items():
        data.append(val)

    return stats.pearsonr(data[0], data[1])


# https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.stats.spearmanr.html
# Parameters: a, b (b is optional) | axis (optional) 
def spearman_corr(iv: VarData, dv: VarData, predictions: list, comp_data: CombinedData, **kwargs):
    assert(len(comp_data.dataframes) == 2)

    data = []
    for key, val in comp_data.dataframes.items():
        # Use numbers for categories in ordinal data
        if (is_ordinal(dv.metadata['dtype'])):
            numeric = [dv.metadata['categories'][x] for x in val]
            val = numeric

        data.append(val)

    return stats.spearmanr(data[0], data[1])


# https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.stats.linregress.html
# Parameters: x (array-like) | y (array-like)
def linear_regression(iv: VarData, dv: VarData, predictions: list, comp_data: CombinedData, **kwargs):
    import pdb; pdb.set_trace()
    return stats.linregress(iv.dataframe, dv.dataframe)
    

## NAIVE IMPLEMENTATION RIGHT NOW
# TODO: depending on ow linear constraing solver is implemented, may want to have two separate functions - 1) returns the name of the test/function and 2) get test with parameters, but not executed??
# Based on the properties of data, find the most appropriate test to conduct
# Return the test but do not execute
# def find_test(dataset: Dataset, comp_data: CombinedData, iv, dv, predictions, design: Dict[str, str], **kwargs):
#     # Two IV groups (only applies to nominal/ordinal IVs)
#     if (len(comp_data.dataframes) == 2):
#         if (is_nominal(iv.metadata['dtype']) and is_independent_samples(iv.metadata['var_name'], design)):
#             if (is_numeric(dv.metadata['dtype']) and is_normal(comp_data, kwargs['alpha'])):
#                 return lambda : t_test_ind(iv, dv, predictions, comp_data, **kwargs)
#             elif (is_numeric(dv.metadata['dtype']) or is_ordinal(dv.metadata['dtype'])):
#                 return lambda : mann_whitney_u(iv, dv, predictions, comp_data, **kwargs)
#             elif (is_nominal(dv.metadata['dtype'])):
#                 raise AssertionError('Not sure if Fishers is the correct test here - what if have more than 2 x 2 table??')
#                 return lambda : fishers_exact(iv, dv, predictions, comp_data, **kwargs)
#         elif (is_nominal(iv.metadata['dtype']) and is_dependent_samples(iv.metadata['var_name'], design)):
#             if (is_numeric(dv.metadata['dtype']) and is_normal(comp_data, kwargs['alpha'])):
#                 return lambda : t_test_paired(iv, dv, predictions, comp_data, **kwargs)
#             elif (is_numeric(dv.metadata['dtype']) or is_ordinal(dv.metadata['dtype'])):
#                 return lambda : wilcoxon_signed_rank(iv, dv, predictions, comp_data, **kwargs)
#             elif (is_nominal(dv.metadata['dtype'])):
#                 raise AssertionError('Not sure if McNemar is the correct test here - what if have more than 2 x 2 table??')
#         elif (is_numeric(iv.metadata['dtype'])): # OR MOVE TO/REPEAT in outer IF/ELSE for comp_data.dataframes == 1??
#             if (is_numeric(dv.metadata['dtype'])):
#                 # Check normal distribution of both variables
#                 if (is_normal(comp_data, kwargs['alpha'], comp_data.dataframes[dv.metadata['var_name']])):
#                     # Check homoscedasticity
#                     if (comp_data.properties.var[1] < kwargs['alpha']): 
#                         return lambda : linear_regression(iv, dv, predictions, comp_data, **kwargs)
#                     else:  
#                         return lambda : pearson_corr(iv, dv, predictions, comp_data, **kwargs)
#                 else: 
#                     return lambda : spearman_corr(iv, dv, predictions, comp_data, **kwargs)
#             elif (is_numeric(dv.metadata['dtype']) or is_ordinal(dv.metadata['dtype'])):
#                 return lambda : spearman_corr(iv, dv, predictions, comp_data, **kwargs)
#             elif (is_nominal(dv.metadata['dtype'])):
#                 # TODO depends on the number of outcome categories for nominal variable
#                 raise AssertionError ('Not implemnted - simple logistic regression')
#     elif (len(comp_data.dataframes) > 2):
#         raise NotImplementedError
#     else: 
#         raise AssertionError('Trying to compare less than 1 variables....?')

                

# This is the function used to determine and then execute test based on CombinedData
def execute_test(dataset: Dataset, data_props: CombinedData, iv: VarData, dv: VarData, predictions: list, design: Dict[str,str]): 
    # For power we need sample size, effect size, alpha
    sample_size = 0
    # calculate sample size
    for df in data_props.dataframes:
        sample_size += len(data_props.dataframes[df])

    effect_size = design['effect size'] if ('effect size' in design) else [.2, .5, .8] # default range unless user defines
    
    alpha = design['alpha'] if ('alpha' in design) else .05
    
    # Find test
    stat_test = find_test(dataset, data_props, iv, dv, predictions, design, sample_size=sample_size, effect_size=effect_size, alpha=alpha)
    
    # Execute test
    if stat_test: 
        results = stat_test()
    else: 
        results = bootstrap()
    stat_test_name = results.__class__.__name__

    # Wrap results in ResData and return
    return ResData(iv=iv.metadata['var_name'], dv=dv.metadata['var_name'], test_name=stat_test_name, results=results, properties=data_props.properties, predictions=predictions)
    
# def bootstrap(data):
def bootstrap():
    print('Do something with incoming data')

# Returns the function that has the @param name
def lookup_function(name): 
    return globals()[name.lower()]

def execute_tests(dataset, combined_data: CombinedData, tests: Dict[Tests, Assumptions]): 
    results = dict()

    stats_tests = []
    for test, assumptions in tests.items(): 
        stats_tests.append(test)

    for t in stats_tests: 
        # Look up the function call for each test
        t_info = t.__dict__
        t_name = t_info['_name_']
        test_func = lookup_function(t_name)
        # import pdb; pdb.set_trace()

        # Execute the statistical test
        stat_result = test_func(dataset, combined_data)
        # import pdb; pdb.set_trace()

        # Store results
        results[t] = stat_result

    # Return results
    return results
    


def explanatory_strings_for_assumptions(assumptions: Assumptions) -> List[str]:
    explanation = []
    if assumptions & Assumptions.INDEPENDENT_OBSERVATIONS:
        explanation.append("Assumes independent observations.")
        assumptions &= ~Assumptions.INDEPENDENT_OBSERVATIONS

    if assumptions & Assumptions.NORMALLY_DISTRIBUTED_VARIABLES:
        explanation.append("Assumes samples are normally distributed.")
        assumptions &= ~Assumptions.NORMALLY_DISTRIBUTED_VARIABLES

    if assumptions & Assumptions.NORMALLY_DISTRIBUTED_DIFFERENCE_BETWEEN_VARIABLES:
        explanation.append("Assumes difference between paired values is normally distributed.")
        assumptions &= ~Assumptions.NORMALLY_DISTRIBUTED_DIFFERENCE_BETWEEN_VARIABLES

    if assumptions & Assumptions.SYMMETRICALLY_DISTRIBUTED_DIFFERENCE_BETWEEN_VARIABLES:
        explanation.append("Assumes difference between paired values is symmetrically distributed.")
        assumptions &= ~Assumptions.SYMMETRICALLY_DISTRIBUTED_DIFFERENCE_BETWEEN_VARIABLES

    if assumptions & Assumptions.SIMILAR_VARIANCES:
        explanation.append("Assumes samples have similar variances.")
        assumptions &= ~Assumptions.SIMILAR_VARIANCES

    if assumptions & Assumptions.LARGE_SAMPLE_SIZE:
        explanation.append("Assumes a large enough sample size.")
        assumptions &= ~Assumptions.LARGE_SAMPLE_SIZE

    if assumptions & Assumptions.VALUES_ARE_FREQUENCIES:
        explanation.append("Assumes values are frequencies (and not, e.g., percentages).")
        assumptions &= ~Assumptions.VALUES_ARE_FREQUENCIES

    if assumptions & Assumptions.PAIRED_OBSERVATIONS:
        explanation.append("Assumes observations are paired (e.g. within subjects).")
        assumptions &= ~Assumptions.PAIRED_OBSERVATIONS

    if assumptions & Assumptions.NO_OUTLIERS:
        explanation.append("Assumes there are no outliers in the data.")
        assumptions &= ~Assumptions.NO_OUTLIERS

    if assumptions & Assumptions.NO_OUTLIERS_IN_DIFFERENCE_BETWEEN_VARIABLES:
        explanation.append("Assumes there are no outliers in the difference between paired values.")
        assumptions &= ~Assumptions.NO_OUTLIERS_IN_DIFFERENCE_BETWEEN_VARIABLES

    if assumptions & Assumptions.LINEAR_RELATIONSHIP:
        explanation.append("Assumes there is a linear relationship between the variables.")
        assumptions &= ~Assumptions.LINEAR_RELATIONSHIP

    if assumptions & Assumptions.BIVARIATE_NORMAL_VARIABLES:
        explanation.append("Assumes the two variables have a bivariate normal distribution.")
        assumptions &= ~Assumptions.BIVARIATE_NORMAL_VARIABLES

    if assumptions & Assumptions.RELATED_SAMPLES:
        explanation.append("Assumes the samples come from related sources (e.g. within subjects).")
        assumptions &= ~Assumptions.RELATED_SAMPLES

    if assumptions & Assumptions.MONOTONIC_RELATIONSHIP:
        explanation.append("Assumes there is a monotonic relationship between the variables.")
        assumptions &= ~Assumptions.MONOTONIC_RELATIONSHIP

    if assumptions & Assumptions.ALL_VARIABLES_CONTINUOUS_OR_ORDINAL:
        explanation.append("Assumes all variables are continuous or ordinal.")
        assumptions &= ~Assumptions.ALL_VARIABLES_CONTINUOUS_OR_ORDINAL

    if assumptions & Assumptions.DEPENDENT_VARIABLE_CONTINUOUS_OR_ORDINAL:
        explanation.append("Assumes the dependent variable is continuous or ordinal.")
        assumptions &= ~Assumptions.DEPENDENT_VARIABLE_CONTINUOUS_OR_ORDINAL

    assert assumptions == Assumptions.NONE, \
        "Not all assumptions have a corresponding explanatory string: %s" % assumptions

    return explanation