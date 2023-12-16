

import pytest

import math
import numpy as np
import pandas as pd
from retailoptimizer import RetailProblem, print_avail_solvers
from pulp import LpMinimize, LpProblem, LpStatus, lpSum, LpVariable, LpInteger, LpBinary, makeDict


SOLVER_NAME = 'GLPK_CMD'

def convert_model_variables_to_dict(model):
  lures1 = list(model.quantity_to_order.keys())
  retailers1 = list(model.quantity_to_order[lures1[0]].keys())

  result = {}
  for l in lures1:
    result[l] = {}
    for r in retailers1:
      result[l][r] = model.quantity_to_order[l][r].varValue
  return result

class TestIncludedExamples:
  """Test the problems specified in the Excel files in examples folder"""

  CAN_BUY_EXTRA_LURES_IF_CHEAPER = True
  shipping = [7.0, 4.0] #shipping price in dollars at [retailer1, retailer2]
  free_shipping_threshold = [50.0, 60.0] #Order threshold in dollars to qualify for free shipping @ [r1,r2]
  
  def test_optimize_small(self):
    num_lures_to_buy = [3, 20]

    lures = ["l1", "l2"]   
    retailers = ["r1", "r2"]  
    prices = [[4.99, 5.49],   #price of l1 at [r1, r2]
              [3.99, 3.49]]    #price of l2 at [r1, r2]
    inventory = [[100, 10],    #max number of l1 available at [r1, r2]
                [15, 30]]    #max number of l2 available at [r1, r2]
  
    expected_quantities = {'l1': {'r1': 0, 'r2':3},
                          'l2': {'r1': 0, 'r2':20}}

    p1 = RetailProblem(lures, num_lures_to_buy, retailers, prices,
                      inventory, self.shipping, self.free_shipping_threshold,
                      solver_name=SOLVER_NAME, 
                      can_buy_extra_lures_if_cheaper = self.CAN_BUY_EXTRA_LURES_IF_CHEAPER)
    
    p1.solve()
    
    #check that model found optimal solution
    assert p1.model.status == 1
   
    #check that correct quantities are ordered
    quant_to_order = convert_model_variables_to_dict(p1)
    assert quant_to_order == expected_quantities

    #check total bill
    assert math.isclose(p1.model.objective.value(), 86.27, abs_tol=0.01)

  def test_optimize_large(self):
    lures = ["l1", "l2", 'l3', 'l4', 'l5', 'l6', 'l7', 'l8']   
    retailers = ["r1", "r2"]  
    prices = [[4.99, 5.49],    #price of l1 at [r1, r2]
              [3.99, 3.49],    #price of l2 at [r1, r2]
              [4.99, 5.05],
              [3.29, 3.50],
              [5.25, 5.00],
              [14.99, 15.50],
              [7.99, 7.29],
              [7.99, 7.65]]
    inventory = [[100, 10],    #max number of l1 available at [r1, r2]
                [15, 30],     #max number of l2 available at [r1, r2]
                [100, 100],
                [100, 100],
                [100, 100],
                [100, 100],
                [0, 10],
                [100,100]]

    num_lures_to_buy = [8, 2,5,2,1,1,1,1]

    expected_quantities = {'l1': {'r1': 8, 'r2':0},
                            'l2': {'r1': 0, 'r2':2},
                            'l3': {'r1': 1, 'r2':4},
                            'l4': {'r1': 2, 'r2':0},
                            'l5': {'r1': 0, 'r2':1},
                            'l6': {'r1': 0, 'r2':1},
                            'l7': {'r1': 0, 'r2':1},
                            'l8': {'r1': 0, 'r2':1}
                            }

    p1 = RetailProblem(lures, num_lures_to_buy, retailers, prices,
                      inventory, self.shipping, self.free_shipping_threshold,
                      solver_name=SOLVER_NAME, 
                      can_buy_extra_lures_if_cheaper = self.CAN_BUY_EXTRA_LURES_IF_CHEAPER)
    p1.solve()
    
    #Check that model found optimal solution
    assert p1.model.status == 1

    #check that correct quantities are ordered
    quant_to_order = convert_model_variables_to_dict(p1)
    assert quant_to_order == expected_quantities

    #check total bill
    assert math.isclose(p1.model.objective.value(), 114.11, abs_tol=0.01)


class TestClassExtraExamples:
  """Some additional examples, focused on ordering additional items to 
  achieve free shipping and reduce overall prices"""

  CAN_BUY_EXTRA_LURES_IF_CHEAPER = True
  shipping = [6.75, 3.99] #shipping price in dollars at [retailer1, retailer2]
  free_shipping_threshold = [50.0, 59.0] #Order threshold in dollars to qualify for free shipping @ [r1,r2]
  lures = ["l1", "l2"]   
  retailers = ["r1", "r2"]  
  prices = [[4.99, 5.49],   #price of l1 at [r1, r2]
            [3.99, 3.49]]   #price of l2 at [r1, r2]
  inventory = [[100, 10],   #max number of l1 available at [r1, r2]
               [15, 30]]    #max number of l2 available at [r1, r2]
  
  @pytest.mark.parametrize("num_lures_to_buy,expected_quantities,total_bill", [
    ([0, 16], {'l1': {'r1': 0, 'r2':0},
               'l2': {'r1': 0, 'r2':17}},  #buy 1 extra l2 lure to get free shipping -> buy 17 instead of 16 
               59.33), 

    ([10, 0], {'l1': {'r1': 10, 'r2':0}, 
               'l2': {'r1': 1, 'r2':0}},  #buy 1 extra l2 lure to get free shipping --> buy 1 instead of 0
              53.89)
  ])
  def test_optimize_order_extra_lure_for_free_shipping1(self, num_lures_to_buy, expected_quantities, total_bill):
    p1 = RetailProblem(self.lures, num_lures_to_buy, self.retailers, self.prices,
                      self.inventory, self.shipping, self.free_shipping_threshold,
                      solver_name=SOLVER_NAME, 
                      can_buy_extra_lures_if_cheaper = self.CAN_BUY_EXTRA_LURES_IF_CHEAPER)
    p1.solve()
    
    #check that model found optimal solution
    assert p1.model.status == 1

    quant_to_order = convert_model_variables_to_dict(p1)
    #check that correct quantities are ordered
    assert quant_to_order == expected_quantities

    #check total bill
    assert math.isclose(p1.model.objective.value(), total_bill, abs_tol=0.01)
