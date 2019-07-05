from .value import Value

import attr

@attr.s(init=True)
class TestResult(Value): 
    name = attr.ib()
    test_statistic = attr.ib()
    p_value = attr.ib()
    
    def adjust_p_val(self, correction): 
        self.adjusted_p_val = attr.ib()
        self.adjusted_p_val = self.p_value/correction
        # import pdb; pdb.set_trace()
    
    def set_adjusted_p_val(self, adjusted_p_val): 
        self.adjusted_p_val = attr.ib()
        self.adjusted_p_val = adjusted_p_val

    def add_effect_size(self, name, effect_size): 
        if hasattr(self, 'effect_size'):
            # additional_effect_size = {name : effect_size}
            self.effect_size[name] = effect_size
        else: 
            self.effect_size = attr.ib()
            self.effect_size = {name : effect_size}
    
    # def __str__(self): 
        