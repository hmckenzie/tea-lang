from .ast import *
from .dataset import Dataset
from .evaluate_data_structures import VarData, CompData, ResData # runtime data structures
from .evaluate_helper_methods import compute_data_properties, execute_test

import attr
from typing import Any
from types import SimpleNamespace # allows for dot notation access for dictionaries

from scipy import stats # Stats library used
import statsmodels.api as sm
import statsmodels.formula.api as smf
import numpy as np # Use some stats from numpy instead
import pandas as pd
import bootstrapped as bs

# TODO: Pass effect size and alpha value as part of experimental design -- these are used to optimize for power
def evaluate(dataset: Dataset, expr: Node, design: Dict[str, str]=None):
    if isinstance(expr, Variable):
        dataframe = dataset[expr.name]
        # import pdb; pdb.set_trace()
        metadata = dataset.get_variable_data(expr.name) # (dtype, categories)
        return VarData(dataframe, metadata)

    elif isinstance(expr, Literal):
        data = pd.Series([expr.value] * len(dataset.data), index=dataset.data.index) # Series filled with literal value
        metadata = None # metadata=None means literal
        return VarData(data, metadata)

    elif isinstance(expr, Equal):
        lhs = evaluate(dataset, expr.lhs)
        rhs = evaluate(dataset, expr.rhs)
        assert isinstance(lhs, VarData)
        assert isinstance(rhs, VarData)
        
        dataframe = lhs.dataframe[lhs.dataframe == rhs.dataframe]
        metadata = lhs.metadata
        return VarData(dataframe, metadata)

    elif isinstance(expr, NotEqual): 
        rhs = evaluate(dataset, expr.rhs)
        lhs = evaluate(dataset, expr.lhs)
        assert isinstance(rhs, VarData)
        assert isinstance(lhs, VarData)
        
        dataframe = lhs.dataframe[lhs.dataframe != rhs.dataframe]
        metadata = lhs.metadata
        return VarData(dataframe, metadata)

    elif isinstance(expr, LessThan):
        lhs = evaluate(dataset, expr.lhs)
        rhs = evaluate(dataset, expr.rhs)
        assert isinstance(lhs, VarData)
        assert isinstance(rhs, VarData)


        dataframe = None
        metadata = rhs.metadata
        
        if (not lhs.metadata):
            raise ValueError('Malformed Relation. Filter on Variables must have variable as rhs')
        elif (lhs.metadata['dtype'] is DataType.NOMINAL):
            raise ValueError('Cannot compare nominal values with Less Than')
        elif (lhs.metadata['dtype'] is DataType.ORDINAL):
            assert (rhs.metadata is None) # May want to add a case should RHS and LHS both be variables
            comparison = rhs.dataframe.iloc[0]
            if (isinstance(comparison, str)):
                categories = lhs.metadata['categories'] # OrderedDict
                # Get raw Pandas Series indices for desired data
                ids  = [i for i,x in enumerate(lhs.dataframe) if categories[x] < categories[comparison]]
                # Get Pandas Series set indices for desired data
                p_ids = [lhs.dataframe.index.values[i] for i in ids]
                # Create new Pandas Series with only the desired data, using set indices
                dataframe = pd.Series(lhs.dataframe, p_ids)
                dataframe.index.name = dataset.pid_col_name
                
            elif (np.issubdtype(comparison, np.integer)):
                categories = lhs.metadata['categories'] # OrderedDict
                # Get raw Pandas Series indices for desired data
                ids  = [i for i,x in enumerate(lhs.dataframe) if categories[x] < comparison]
                # Get Pandas Series set indices for desired data
                p_ids = [lhs.dataframe.index.values[i] for i in ids]
                # Create new Pandas Series with only the desired data, using set indices
                dataframe = pd.Series(lhs.dataframe, p_ids)
                dataframe.index.name = dataset.pid_col_name                

            else: 
                raise ValueError(f"Cannot compare ORDINAL variables to {type(rhs.dataframe.iloc[0])}")


        elif (lhs.metadata['dtype'] is DataType.INTERVAL or lhs.metadata['dtype'] is DataType.RATIO):
            comparison = rhs.dataframe.iloc[0]
             # Get raw Pandas Series indices for desired data
            ids  = [i for i,x in enumerate(lhs.dataframe) if x < comparison]
            # Get Pandas Series set indices for desired data
            p_ids = [lhs.dataframe.index.values[i] for i in ids]
            # Create new Pandas Series with only the desired data, using set indices
            dataframe = pd.Series(lhs.dataframe, p_ids)
            dataframe.index.name = dataset.pid_col_name   

        else:
            raise Exception(f"Invalid Less Than Operation:{lhs} < {rhs}")

        
        return VarData(dataframe, metadata)

    elif isinstance(expr, LessThanEqual):
        lhs = evaluate(dataset, expr.lhs)
        rhs = evaluate(dataset, expr.rhs)
        assert isinstance(lhs, VarData)
        assert isinstance(rhs, VarData)


        dataframe = None
        metadata = rhs.metadata
        
        if (not lhs.metadata):
            raise ValueError('Malformed Relation. Filter on Variables must have variable as rhs')
        elif (lhs.metadata['dtype'] is DataType.NOMINAL):
            raise ValueError('Cannot compare nominal values with Less Than')
        elif (lhs.metadata['dtype'] is DataType.ORDINAL):
            assert (rhs.metadata is None) # May want to add a case should RHS and LHS both be variables
            comparison = rhs.dataframe.iloc[0]
            if (isinstance(comparison, str)):
                categories = lhs.metadata['categories'] # OrderedDict
                # Get raw Pandas Series indices for desired data
                ids  = [i for i,x in enumerate(lhs.dataframe) if categories[x] <= categories[comparison]]
                # Get Pandas Series set indices for desired data
                p_ids = [lhs.dataframe.index.values[i] for i in ids]
                # Create new Pandas Series with only the desired data, using set indices
                dataframe = pd.Series(lhs.dataframe, p_ids)
                dataframe.index.name = dataset.pid_col_name
                
            elif (np.issubdtype(comparison, np.integer)):
                categories = lhs.metadata['categories'] # OrderedDict
                # Get raw Pandas Series indices for desired data
                ids  = [i for i,x in enumerate(lhs.dataframe) if categories[x] <= comparison]
                # Get Pandas Series set indices for desired data
                p_ids = [lhs.dataframe.index.values[i] for i in ids]
                # Create new Pandas Series with only the desired data, using set indices
                dataframe = pd.Series(lhs.dataframe, p_ids)
                dataframe.index.name = dataset.pid_col_name                

            else: 
                raise ValueError(f"Cannot compare ORDINAL variables to {type(rhs.dataframe.iloc[0])}")


        elif (lhs.metadata['dtype'] is DataType.INTERVAL or lhs.metadata['dtype'] is DataType.RATIO):
            comparison = rhs.dataframe.iloc[0]
             # Get raw Pandas Series indices for desired data
            ids  = [i for i,x in enumerate(lhs.dataframe) if x <= comparison]
            # Get Pandas Series set indices for desired data
            p_ids = [lhs.dataframe.index.values[i] for i in ids]
            # Create new Pandas Series with only the desired data, using set indices
            dataframe = pd.Series(lhs.dataframe, p_ids)
            dataframe.index.name = dataset.pid_col_name   

        else:
            raise Exception(f"Invalid Less Than Equal Operation:{lhs} <= {rhs}")


        return VarData(dataframe, metadata)
    
    elif isinstance(expr, GreaterThan):
        lhs = evaluate(dataset, expr.lhs)
        rhs = evaluate(dataset, expr.rhs)
        assert isinstance(lhs, VarData)
        assert isinstance(rhs, VarData)


        dataframe = None
        metadata = rhs.metadata
        
        if (not lhs.metadata):
            raise ValueError('Malformed Relation. Filter on Variables must have variable as rhs')
        elif (lhs.metadata['dtype'] is DataType.NOMINAL):
            raise ValueError('Cannot compare nominal values with Greater Than')
        elif (lhs.metadata['dtype'] is DataType.ORDINAL):
            assert (rhs.metadata is None) # May want to add a case should RHS and LHS both be variables
            comparison = rhs.dataframe.iloc[0]
            if (isinstance(comparison, str)):
                categories = lhs.metadata['categories'] # OrderedDict
                # Get raw Pandas Series indices for desired data
                ids  = [i for i,x in enumerate(lhs.dataframe) if categories[x] > categories[comparison]]
                # Get Pandas Series set indices for desired data
                p_ids = [lhs.dataframe.index.values[i] for i in ids]
                # Create new Pandas Series with only the desired data, using set indices
                dataframe = pd.Series(lhs.dataframe, p_ids)
                dataframe.index.name = dataset.pid_col_name
                
            elif (np.issubdtype(comparison, np.integer)):
                categories = lhs.metadata['categories'] # OrderedDict
                # Get raw Pandas Series indices for desired data
                ids  = [i for i,x in enumerate(lhs.dataframe) if categories[x] > comparison]
                # Get Pandas Series set indices for desired data
                p_ids = [lhs.dataframe.index.values[i] for i in ids]
                # Create new Pandas Series with only the desired data, using set indices
                dataframe = pd.Series(lhs.dataframe, p_ids)
                dataframe.index.name = dataset.pid_col_name                

            else: 
                raise ValueError(f"Cannot compare ORDINAL variables to {type(rhs.dataframe.iloc[0])}")


        elif (lhs.metadata['dtype'] is DataType.INTERVAL or lhs.metadata['dtype'] is DataType.RATIO):
            comparison = rhs.dataframe.iloc[0]
             # Get raw Pandas Series indices for desired data
            ids  = [i for i,x in enumerate(lhs.dataframe) if x > comparison]
            # Get Pandas Series set indices for desired data
            p_ids = [lhs.dataframe.index.values[i] for i in ids]
            # Create new Pandas Series with only the desired data, using set indices
            dataframe = pd.Series(lhs.dataframe, p_ids)
            dataframe.index.name = dataset.pid_col_name   

        else:
            raise Exception(f"Invalid Greater Than Operation:{lhs} > {rhs}")

        return VarData(dataframe, metadata) 
   
    elif isinstance(expr, GreaterThanEqual):
        lhs = evaluate(dataset, expr.lhs)
        rhs = evaluate(dataset, expr.rhs)
        assert isinstance(lhs, VarData)
        assert isinstance(rhs, VarData)


        dataframe = None
        metadata = rhs.metadata
        
        if (not lhs.metadata):
            raise ValueError('Malformed Relation. Filter on Variables must have variable as rhs')
        elif (lhs.metadata['dtype'] is DataType.NOMINAL):
            raise ValueError('Cannot compare nominal values with Greater Than Equal')
        elif (lhs.metadata['dtype'] is DataType.ORDINAL):
            assert (rhs.metadata is None) # May want to add a case should RHS and LHS both be variables
            comparison = rhs.dataframe.iloc[0]
            if (isinstance(comparison, str)):
                categories = lhs.metadata['categories'] # OrderedDict
                # Get raw Pandas Series indices for desired data
                ids  = [i for i,x in enumerate(lhs.dataframe) if categories[x] >= categories[comparison]]
                # Get Pandas Series set indices for desired data
                p_ids = [lhs.dataframe.index.values[i] for i in ids]
                # Create new Pandas Series with only the desired data, using set indices
                dataframe = pd.Series(lhs.dataframe, p_ids)
                dataframe.index.name = dataset.pid_col_name
                
            elif (np.issubdtype(comparison, np.integer)):
                categories = lhs.metadata['categories'] # OrderedDict
                # Get raw Pandas Series indices for desired data
                ids  = [i for i,x in enumerate(lhs.dataframe) if categories[x] >= comparison]
                # Get Pandas Series set indices for desired data
                p_ids = [lhs.dataframe.index.values[i] for i in ids]
                # Create new Pandas Series with only the desired data, using set indices
                dataframe = pd.Series(lhs.dataframe, p_ids)
                dataframe.index.name = dataset.pid_col_name                

            else: 
                raise ValueError(f"Cannot compare ORDINAL variables to {type(rhs.dataframe.iloc[0])}")


        elif (lhs.metadata['dtype'] is DataType.INTERVAL or lhs.metadata['dtype'] is DataType.RATIO):
            comparison = rhs.dataframe.iloc[0]
             # Get raw Pandas Series indices for desired data
            ids  = [i for i,x in enumerate(lhs.dataframe) if x >= comparison]
            # Get Pandas Series set indices for desired data
            p_ids = [lhs.dataframe.index.values[i] for i in ids]
            # Create new Pandas Series with only the desired data, using set indices
            dataframe = pd.Series(lhs.dataframe, p_ids)
            dataframe.index.name = dataset.pid_col_name   

        else:
            raise Exception(f"Invalid Greater Than Equal Operation:{lhs} >= {rhs}")

        return VarData(dataframe, metadata) 

    # elif isinstance(expr, Relate): 
    #     raise Exception('Not implemented RELATE')

    elif isinstance(expr, Compare): 
        
        import pdb; pdb.set_trace()
              
        data_props = compute_data_properties(dataset, expr) 

        res = execute_test(dataset, expr, data_props, design) # design contains info about between/within subjects AND Power parameters (alpha, effect size, sample size - which can be calculated)

        import pdb; pdb.set_trace()  

    elif isinstance(expr, Mean):
        var = evaluate(dataset, expr.var)
        assert isinstance(var, VarData)

        bs.bootstrap(var.dataframe, stat_func=bs_stats.mean)
        raise Exception('Not implemented Mean')
    
    # elif isinstance(expr, Median):
    #     raise Exception('Not implemented Median')


    
    # elif isinstance(expr, Add): 
    #     raise Exception('Not implemented Add')

    # TODO all the other arithmetic....