"""Unit tests for retailoptimizer.py"""
import pytest
import math
import numpy as np
import pandas as pd
from online_purchase_optimizer.retailoptimizer import RetailProblem, print_avail_solvers
from pulp import LpMinimize, LpProblem, LpStatus, lpSum, LpVariable, LpInteger, LpBinary, makeDict

SOLVER_NAME = 'PULP_CBC_CMD'
# SOLVER_NAME = 'GLPK_CMD'

optimization_params_example_problems = [
  #small example: order all items from retailer 2
  {'lures':              ["l1", "l2"],
    'num_lures_to_buy':  [3, 20],
    'prices':            [[4.99, 5.49],    #price of l1 at [r1, r2]
                          [3.99, 3.49]],   #price of l2 at [r1, r2]
    'inventory':         [[100, 10],       #max number of l1 available at [r1, r2]
                          [15, 30]],       #max number of l2 available at [r1, r2]
    'expected_quantities': {'l1': {'r1': 0, 'r2':3},  #buy everyting at r2 retailer so get free shipping
                            'l2': {'r1': 0, 'r2':20}},
    'expected_bill':      86.27
  },

  #large example: split order amongst retailers r1 and r2
  {'lures':              ["l1", "l2", 'l3', 'l4', 'l5', 'l6', 'l7', 'l8'],
    'num_lures_to_buy':  [8, 2, 5, 2, 1, 1, 1, 1],
    'lures':             ["l1", "l2", 'l3', 'l4', 'l5', 'l6', 'l7', 'l8'],
    'num_lures_to_buy':  [8, 2, 5, 2, 1, 1, 1, 1],
    'prices':            [[4.99, 5.49],    #price of l1 at [r1, r2]
                          [3.99, 3.49],    #price of l2 at [r1, r2]
                          [4.99, 5.05],
                          [3.29, 3.50],
                          [5.25, 5.00],
                          [14.99, 15.50],
                          [7.99, 7.29],
                          [7.99, 7.65]],
    'inventory':         [[100, 10],    #max number of l1 available at [r1, r2]
                          [15, 30],     #max number of l2 available at [r1, r2]
                          [100, 100],
                          [100, 100],
                          [100, 100],
                          [100, 100],
                          [0, 10],
                          [100,100]],
    'expected_quantities': {'l1': {'r1': 8, 'r2':0},
                            'l2': {'r1': 0, 'r2':2},
                            'l3': {'r1': 1, 'r2':4}, #order 1 lure at more expensive r1 to qualify for free shipping, order 4 at cheaper r2
                            'l4': {'r1': 2, 'r2':0},
                            'l5': {'r1': 0, 'r2':1},
                            'l6': {'r1': 0, 'r2':1},
                            'l7': {'r1': 0, 'r2':1},
                            'l8': {'r1': 0, 'r2':1}
                            },
    'expected_bill':      114.11
}]

labels_example_problems = ("sample-order-small", "sample-order-large")

class TestIncludedExamples:
  """Test the problems specified in the Excel files in examples folder"""

  CAN_BUY_EXTRA_LURES_IF_CHEAPER = True
  retailers = ["r1", "r2"] 
  shipping = [7.0, 4.0] #shipping price in dollars at [retailer1, retailer2]
  free_shipping_threshold = [50.0, 60.0] #Order threshold in dollars to qualify for free shipping @ [r1,r2]
  
  @pytest.mark.parametrize("problem_params", optimization_params_example_problems,
    ids=labels_example_problems)
  def test_optimize(self, problem_params):
    r = problem_params

    p1 = RetailProblem(r['lures'], r['num_lures_to_buy'], self.retailers, r['prices'],
                       r['inventory'], self.shipping, self.free_shipping_threshold,
                       solver_name=SOLVER_NAME, 
                       can_buy_extra_lures_if_cheaper = self.CAN_BUY_EXTRA_LURES_IF_CHEAPER)
    
    p1.solve()

    #check that model found optimal solution
    assert p1.model.status == 1
   
    #check that correct quantities are ordered
    quant_to_order = p1.convert_model_variable_quantities_to_dict()
    assert quant_to_order == r['expected_quantities']

    #check total bill
    assert math.isclose(p1.model.objective.value(), r['expected_bill'], abs_tol=0.01)

#-------------------------------------------------------------------------------
    
optimization_params_extra_problems = (
  #Test not allowing buying extra lures to qualify for free shipping
  {'num_lures_to_buy':    [0, 16], 
    'expected_quantities': {'l1': {'r1': 0, 'r2':0}, 
                            'l2': {'r1': 0, 'r2':16}}, 
    'total_bill':          59.83,        #total_bill = 16*3.49 + 3.99 = 59.83
    'can_buy_extra_lures': False},             
  
  {'num_lures_to_buy':    [0, 17], 
    'expected_quantities': {'l1': {'r1': 0, 'r2':0}, 
                            'l2': {'r1': 0, 'r2':17}}, #get free shipping when order 17 l2 lures vs 16, so cheaper
    'total_bill':          59.33,       #total_bill = 17*3.49 = 59.33
    'can_buy_extra_lures': False},              
  
  {'num_lures_to_buy':    [10, 0], 
    'expected_quantities': {'l1': {'r1': 10, 'r2':0}, 
                            'l2': {'r1': 0, 'r2':0}},   
    'total_bill':          56.65,       #must pay for shipping: total_bill = 10*4.99 + 6.75 = 56.65
    'can_buy_extra_lures': False},              

  {'num_lures_to_buy':    [11, 0], 
    'expected_quantities': {'l1': {'r1': 11, 'r2':0}, 
                            'l2': {'r1': 0, 'r2':0}},  
    'total_bill':          54.89,        #Get free shipping with 11 lures: 11*4.99 = 54.89, cheaper than ordering 10
    'can_buy_extra_lures': False},              
  #---------------------------
  #Test automatically buying extra lures to qualify for free shipping if it lowers overall bill.

  {'num_lures_to_buy':    [10, 0], 
    'expected_quantities': {'l1': {'r1': 10, 'r2':0}, 
                            'l2': {'r1': 1, 'r2':0}},  #automatically buy 1 extra l2 lure to get free shipping --> buy 1 instead of 0 --> it's cheaper
    'total_bill':          53.89, 
    'can_buy_extra_lures': True},        #10*4.99 + 1*3.99 = 53.89

  {'num_lures_to_buy':    [0, 16], 
    'expected_quantities': {'l1': {'r1': 0, 'r2':0},
                            'l2': {'r1': 0, 'r2':17}},  #automatically buy 1 extra l2 lure to get free shipping -> buy 17 instead of 16 
    'total_bill':          59.33,        #17*3.49 = 59.33  
    'can_buy_extra_lures': True}                     
)

labels_extra_problems = ('pay-shipping-l2=16', 'free-shipping-l2=17', 'pay-shipping-l1=10', 'free-shipping-l1=11',
  'order-extra-for-free-shipping-l1=10,l2=1', 'order-extra-for-free-shipping-l1=16,l2=1')

class TestExtraExamples:
  """Some additional examples, focused on enabling/disabling the ordering of
  additional items to qualify for free shipping and reduce the overall bill"""

  shipping = [6.75, 3.99] #shipping price in dollars at [retailer1, retailer2]
  free_shipping_threshold = [50.0, 59.0] #Order threshold in dollars to qualify for free shipping @ [r1,r2]
  lures = ["l1", "l2"]   
  retailers = ["r1", "r2"]  
  prices = [[4.99, 5.49],   #price of l1 at [r1, r2]
            [3.99, 3.49]]   #price of l2 at [r1, r2]
  inventory = [[100, 10],   #max number of l1 available at [r1, r2]
               [15, 30]]    #max number of l2 available at [r1, r2]
  
  @pytest.mark.parametrize("problem_params", optimization_params_extra_problems, 
    ids=labels_extra_problems)
  def test_optimize(self, problem_params):
    r = problem_params

    p1 = RetailProblem(self.lures, r['num_lures_to_buy'], self.retailers, self.prices,
                      self.inventory, self.shipping, self.free_shipping_threshold,
                      solver_name=SOLVER_NAME, 
                      can_buy_extra_lures_if_cheaper = r['can_buy_extra_lures'])
    p1.solve()
    
    #check that model found optimal solution
    assert p1.model.status == 1

    #check that correct quantities are ordered
    quant_to_order = p1.convert_model_variable_quantities_to_dict()
    assert quant_to_order == r['expected_quantities']

    #check total bill
    assert math.isclose(p1.model.objective.value(), r['total_bill'], abs_tol=0.01)

#-------------------------------------------------------------------------------
    
def test_infeasible_problem():
  """This problem has no solution, as the # of lures exceeds inventory"""
  CAN_BUY_EXTRA_LURES_IF_CHEAPER = True
  shipping = [7.0, 4.0] #shipping price in dollars at [retailer1, retailer2]
  free_shipping_threshold = [50.0, 60.0] #Order threshold in dollars to qualify for free shipping @ [r1,r2]
  
  lures = ["l1", "l2"]  
  num_lures_to_buy = [111, 20] # number of l1 lures exceeds total inventory
    
  retailers = ["r1", "r2"]  
  prices = [[4.99, 5.49],   #price of l1 at [r1, r2]
            [3.99, 3.49]]   #price of l2 at [r1, r2]
  inventory = [[100, 10],   #max number of l1 available at [r1, r2]
                [15, 30]]    #max number of l2 available at [r1, r2]

  expected_quantities = {'l1': {'r1': 0, 'r2':3},  #buy everyting at r2 retailer so get free shipping
                          'l2': {'r1': 0, 'r2':20}}

  p1 = RetailProblem(lures, num_lures_to_buy, retailers, prices,
                    inventory, shipping, free_shipping_threshold,
                    solver_name=SOLVER_NAME, 
                    can_buy_extra_lures_if_cheaper = CAN_BUY_EXTRA_LURES_IF_CHEAPER)
  
  p1.solve()
  
  assert p1.model.status == -1  #Infeasible, aka no solution exists
  