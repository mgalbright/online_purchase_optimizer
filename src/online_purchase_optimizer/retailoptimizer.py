#!/usr/bin/python3
"""Class to solve online retail optimization problems
"""

import os
import argparse
import re
import numpy as np
import pandas as pd
from pulp import LpMinimize, LpProblem, LpStatus, lpSum, LpVariable, LpInteger
from pulp import LpBinary, LpContinuous, makeDict, get_solver, listSolvers
from openpyxl import load_workbook

# Helper functions
def list_avail_solvers():
  """List optimzation solvers available to PULP
  
  Returns a list of all solvers currently installed and configured to work
  with PULP.
  """
  return listSolvers(onlyAvailable=True)

def print_avail_solvers():
  for s in list_avail_solvers():
    print(s)

def _format_string(s):
  """Reformat strings so they can be displayed well.
  
  Replace non alpha-numeric characters with '-' and convert to lower case."""
  return re.sub('[^0-9a-z]+', '-', s.lower())

def _format_list_strings(l):
  return [_format_string(s) for s in l]

#----------------------------------------

class RetailProblem:
  """Optimize retail purchase choices to minimize total price.
  
  Typical usage:
    p1 = RetailProblem.load_from_excel('my_excel_file.xlsx')
    p1.initialize_optimization_problem()
    p1.solve()

    p1.print_optimization_results()

    #see details about optimal purchase in jupyter notebook:
    p1.df_quantities
    p1.df_bills
  """

  def __init__(self, 
               lures: list[str], 
               num_lures_to_buy: list[int], 
               retailers: list[str], 
               prices: list[list[float]], 
               inventory: list[list[int]], 
               shipping: list,
               free_shipping_threshold: list[float], 
               can_buy_extra_lures_if_cheaper : bool = True,
               solver_name : str = None,
               num_lures_to_buy_is_integer : bool = True):
    """Define a retail optimization problem
     
    Args:
      lures: A list strings of the names of lures to buy.
      num_lures_to_buy: A list of ints specifying the quanity of each lure 
        to buy.
      retailers: A list names of retailers from where items may be 
        purchased
      prices: A list of list of floats where price[l][r] is the price in dollars
        of lure l at retailer r
      inventory: A list of lists of ints where inventory[l][r] is the max
        number of lures l that retailer r has in stock.
      shipping: A list of floats containing the normal shipping price for 
        each retailer.
      free_shipping_threshold: A list of floats listing how much you must spend
        in dollars at a retailer to qualify for free shipping. 
      can_buy_extra_lures_if_cheaper: bool. If True, the program may select more lures 
        than desired if it reduces the overall bill (by qualifying for free
        shipping). If False, the program will order the exact quantity of lures
        desired, even if it may be cheaper to order additional items.
      solver_name: If None, use default solver. If a string, try to load the 
        specified solver. Default solver is probably 'GLPK_CMD'. Solver 
        'PULP_CBC_CMD' is sometimes interesting since it outputs shadow prices 
        (when variables are continuous, not integer). This is an advanced 
        feature. Note that CBC must be installed separately, e.g. by
          conda install -c conda-forge coincbc
        before installing pulp.
      num_lures_to_buy_is_integer: If True, the quantity of lures to buy are
        integers.  You should always pass True.  False is included as an 
        advanced option to enable exploring shadow prices, which are only 
        computed by 'PULP_CBC_CMD' solver for continuous variables, not integer.
     """
    #Check inputs for obvious problems
    if len(num_lures_to_buy) != len(lures):
      raise ValueError("Lengths of lures and num_lures_to_buy are inconsistent.")
    if len(prices) != len(lures):
      raise ValueError("Lengths of lures and prices are inconsistent.")
    if len(inventory) != len(lures):
      raise ValueError("Lenghts of lures and inventory are inconsistent.")
    
    if len(shipping) != len(retailers):
      raise ValueError("Lengths of retailers and shipping are inconsistent")
    if len(free_shipping_threshold) != len(shipping):
      raise ValueError("Lenths of retailers and free_shipping_threshold are inconsistent")

    #----------------------
    #clean up/reformat inputs & store
    
    self.lures = _format_list_strings(lures)
    self.retailers = _format_list_strings(retailers)
    self.lr_combos = [(l, r) for l in self.lures for r in self.retailers]

    self.prices = prices

    #make dict with lure names as keys and number of lures to buy as values
    self.num_lures_to_buy = makeDict([self.lures], num_lures_to_buy)
    #2d nested dict where keys are [lure, retailer] and inventory are values
    self.inventory = makeDict([self.lures, self.retailers], inventory)
    self.prices = makeDict([self.lures, self.retailers], prices)

    self.shipping = makeDict([self.retailers], shipping) 
    self.free_shipping_threshold = makeDict([self.retailers], free_shipping_threshold)
    
    self.can_buy_extra_lures_if_cheaper = can_buy_extra_lures_if_cheaper
    self.solver_name = solver_name
    self.num_lures_to_buy_is_integer = num_lures_to_buy_is_integer
    #-------------------------
    self.M, self.N = self._compute_big_M_constants(self.lures, 
                                                self.retailers, self.inventory)
    
    self.initialize_optimization_problem()

  
  def _compute_big_M_constants(self, lures, retailers, inventory):
    """Computes large constants M, N to enforce shipping constraints.
    
    These are used in the 'big M' technique to enforce shipping constraints in 
    the MIP. This function uses linear algebra to compute M and N values
    from the problem data to ensure M and N are sufficiently large to be
    effective as constraints.
    """
    M = {r:0 for r in retailers}
    N = M.copy()
    for r in retailers:
      M[r] = self.free_shipping_threshold[r] + 1.0

      N[r] = self.free_shipping_threshold[r] + 1.0
      for l in lures:
        N[r] +=  inventory[l][r]
    return M, N

  
  #Factory to create a problem by loading params from an Excel file.
  #Necessary workaround because python doesn't let you overload constructors.
  @classmethod
  def load_from_excel(cls, excel_file: str, can_buy_extra_lures_if_cheaper = True, 
                      solver_name = None, num_lures_to_buy_is_integer = True):
    """Create an optimization problem by loading problem parameters from Excel file.

    Usage: p1 = RetailProblem.load_from_excel(excel_file)
    
    Args:
      excel_file: name of excel file to load
      can_buy_extra_lures_if_cheaper: see description in __init__
      solver_name: see description in __init__
      num_lures_to_buy_is_integer: see description in __init__
    """
  
    df_lures = pd.read_excel(excel_file, sheet_name=0, skiprows=1, index_col = 0)
    df_prices = pd.read_excel(excel_file, sheet_name=1, skiprows=1, index_col = 0)
    df_inventory = pd.read_excel(excel_file, sheet_name=2, skiprows=1, index_col = 0)
    df_shipping = pd.read_excel(excel_file, sheet_name=3, skiprows=1, index_col = 0)

    #Consumer info:
    lures = list(df_lures.index)
    num_lures_to_buy = list(df_lures.iloc[:,0])

    #retailer info
    retailers = list(df_prices.columns)
    prices = df_prices.to_numpy().tolist()
    inventory = df_inventory.to_numpy().tolist()

    shipping = list(df_shipping.iloc[0,:])
    free_shipping_threshold = list(df_shipping.iloc[1,:])

    return cls(lures, num_lures_to_buy, retailers, prices,
              inventory, shipping, free_shipping_threshold,
              can_buy_extra_lures_if_cheaper, solver_name, 
              num_lures_to_buy_is_integer)


  def initialize_optimization_problem(self):
    """Intialize pulp optimization model"""

    #create Pulp model
    self.model = LpProblem("Online retail problem", LpMinimize)

    #----------------
    #Create problem variables to solve for:

    # A dictionary called 'quant' is created to contain the variables for 
    # quanitity of lures ordered
    # E.g. quant[l][r] is number of lures l from retailer r. 
    # Note there is a 0 lower bound on quantities.

    if self.num_lures_to_buy_is_integer:
        self.quantity_to_order = LpVariable.dicts("quant", (self.lures, self.retailers), 
                                         0, None, LpInteger)
    else:
        #FOR EXPERIMENTATION ONLY: make this program continuous, so shadow 
        #prices can be computed (if using CBC solver)
        self.quantity_to_order = LpVariable.dicts("quant", (self.lures, self.retailers), 
                                         0, None, LpContinuous)

    #y binary variable, aka 'pay_shipping' indicator.
    # A dictionary of indicator variables to track if consumer pays for shipping
    self.pay_shipping = LpVariable.dicts("pay_shipping", (self.retailers,), 0, None, LpBinary)

    #z binary variable, aka 'empty_order' indicator.
    # A second dictionary of indicator variables z, tracks if order was empty.
    # If order was empty, z = 1. If not empty, z = 0. Only pay shipping if order not empty.
    self.empty_order = LpVariable.dicts("empty_order", (self.retailers,), 0, None, LpBinary)

    #-------------------------

    #Add objective function to problem:
    self.model += (      
      lpSum([self.prices[l][r] * self.quantity_to_order[l][r] for (l, r) in self.lr_combos])  #cost of items
      + lpSum([self.shipping[r] * self.pay_shipping[r] for r in self.retailers]),    # + cost of shipping
      "sum_of_purchase_costs",
    )

    #Add inventory constraints:
    for l, r in self.lr_combos:
      self.model += (
        self.quantity_to_order[l][r] <= self.inventory[l][r],
        f"constraint_inventory_{l}_{r}",
      )
        
    #Add quantity constraint: 
    # The number of lures supplied from all retailers must be at least the 
    # number desired. Optionally, you might save money by allowing the solver
    # to order more lures than desired if it reduces the total bill (by qualifying for free shipping)
    for l in self.lures:
      if self.can_buy_extra_lures_if_cheaper:
        self.model += (
          #sum over all retailers providing a lure, make sure total number >= desired number
          lpSum([self.quantity_to_order[l][r] for r in self.retailers]) >= self.num_lures_to_buy[l],
          f"constraint_total_quantity_{l}",
        )
      else:
        self.model += (
          #make sure total number of lures exactly matches desired number. 
          lpSum([self.quantity_to_order[l][r] for r in self.retailers]) == self.num_lures_to_buy[l],
          f"constraint_total_quantity_{l}",
        )
        
    #------------
    #If-Then constraints for shipping fees:

    #shipping constraint 1:
    # If order is not empty, force empty_order[r] = 0.  
    # (That will activate second shipping constraint.)
    for r in self.retailers:
      self.model += (
        lpSum([ self.quantity_to_order[l][r] for l in self.lures]) <= self.N[r]*(1 - self.empty_order[r]),
        f"constraint_empty_orders_no_shipping_fee_{r}",
      )

        
    #shipping constraint 2: (only activated if order is not empty)
    # Forces user to pay for shipping if price is below threshold for free shipping
    for r in self.retailers:
      self.model += (
        #for a retailer r: sum over all lures l to compute total bill, - free shipping threshold
        #Warning: don't put the threshold inside the sum or you over count it
        lpSum([self.prices[l][r] * self.quantity_to_order[l][r] for l in self.lures]) 
        - self.free_shipping_threshold[r] + self.M[r] * self.pay_shipping[r]
        >= - self.N[r]*self.empty_order[r] ,
        f"constraint_pay_for_shipping_{r}",
      )
  

  def solve(self):
    """Solve optimization problem to find optimal purchase.
    
    Results are stored in self.model.  
    Problem status  is stored in self.status.
    """

    print(f"solver = {self.solver_name}")
    if self.solver_name is None:
      self.status = self.model.solve()
    else:
      self.solver = get_solver(self.solver_name) #e.g. CBC solver (passing 'PULP_CBC_CMD') enables computation of shadow prices
      self.status = self.model.solve(self.solver)

    #create pandas dataframes storing optimal order solution: 
    # self.df_quantities, storing optimal quantities to order from each retailer
    # self.df_bills, storing details about the bill to each retailer
    self._generate_dataframes_storing_results()

  def print_optimization_results(self):
    """Print problem results after you call solve()"""
    # The status of the solution is printed to the screen
    print("Status:", LpStatus[self.model.status])

    # Each of the variables is printed with its resolved optimum value
    for v in self.model.variables():
        print(v.name, "=", v.varValue)

    # The optimised objective function value is printed to the screen
    print("Total purchase cost = ", self.model.objective.value())

  def convert_model_variable_quantities_to_dict(self):
    """Converts key output (quantities of items to order) to dict of integers"""

    if self.model.status == 1:
      lures1 = list(self.quantity_to_order.keys())
      retailers1 = list(self.quantity_to_order[lures1[0]].keys())

      result_dict = {}
      for l in lures1:
        result_dict[l] = {}
        for r in retailers1:
          result_dict[l][r] = int(self.quantity_to_order[l][r].varValue)
      return result_dict
    else:
      #model has not been solved yet, no results
      print("Warning: Model has not found optimal solution, cannot return outputs")
      return None


  def list_additonal_items_ordered(self):
    """List additional items were ordered beyond those desired.
    
    Additional items may be ordered to reduce the overall bill
    (by securing free shipping)

    Returns:
      dict with keys for lures, values for additional number of lures purchased.
    """
    extra_lures = {}
    for l in self.lures:
      quantitity_bought = 0

      for r in self.retailers:
        quantitity_bought += self.quantity_to_order[l][r].varValue
      
      if quantitity_bought > self.num_lures_to_buy[l]:
        extra_bought = quantitity_bought - self.num_lures_to_buy[l]
        extra_lures[l] = extra_bought
    return extra_lures

  def print_additonal_items_ordered(self):
    """Prints additional items were ordered beyond those desired.
    
    The solver may order additional lures to reduce the overall bill by
    achieving free shipping. Prints a list of those extra items.
    """
    extra_lures = self.list_additonal_items_ordered()

    for l, extra_bought in extra_lures.items():
      print(f"For lure {l}, ordered {extra_bought} additional units" +
                " (more than desired)")

  def _generate_dataframes_storing_results(self):
    """generate pandas dataframes storing optimal order details
    
    Creates class variables:
      self.df_quantities: stores dataframe with optimal quantities of lures
        to order from each retailer
      self.df_bills: stores details about the bills per retailer for the
        optimal order
    """
    
    if self.model.status == 1:
      #build dataframe storing quantity of lures to order

      quant = {}  #quantity of lures to order from each retailer
      for l in self.lures:
        quant[l] = {}
        for r in self.retailers:
          quant[l][r] = int(self.quantity_to_order[l][r].varValue)
      df_quant = pd.DataFrame(quant).T

      num_lures_total = []  #total number of lures ordered across all retailers
      for l in self.lures:
        num_lures_ordered = 0
        for r in self.retailers:
          num_lures_ordered += quant[l][r]
        num_lures_total.append(num_lures_ordered)
      df_quant['total_number'] = num_lures_total

      self.df_quantities = df_quant
          
      #-------------------------------
      #create dataframw tih info on the bill (total spending) 
      total_bills = []
      shipping_bills = []
      item_bills = []
      for r in self.retailers:
        shipping_bill = (self.pay_shipping[r].varValue) * self.shipping[r]
        
        item_bill = 0
        for l in self.lures:
          item_bill += quant[l][r] * self.prices[l][r]
        
        total_bill = shipping_bill + item_bill
        
        item_bills.append(item_bill)
        shipping_bills.append(shipping_bill)
        total_bills.append(total_bill)

      df_bills = {'total_bill': total_bills, 'shipping_bill': shipping_bills, 
                  'item_bill': item_bills}
      df_bills = pd.DataFrame(df_bills).T
      df_bills.columns = self.retailers
      df_bills['total'] = df_bills.sum(axis=1) #compute totals across all retailers

      self.df_bills = df_bills
    
    else:
      print("Warning: model did not find optimal solution")
      self.df_quantities = None
      self.df_bills = None


  def save_results_to_excel(self, excel_results_file:str,
                            sheet_name_for_quantities = "number_of_lures_to_order",
                            sheet_name_for_total_bills = "bill_info"):
    """Saves key solution results to Excel for easy viewing.
    
    Args:
      excel_results_file: file name where to save key outputs/results.
      sheet_name_for_quantities: name of excel sheet to create which stores
        number of lures to create.
      sheet_name_for_total_bills: name of excel sheet to create which stores
        details about the bill.
    """
    with pd.ExcelWriter(excel_results_file, mode='w') as writer:  
      self.df_quantities.to_excel(writer, sheet_name=sheet_name_for_quantities, index=True)
      self.df_bills.to_excel(writer, sheet_name=sheet_name_for_total_bills, index=True)

#-------------------------------------------------------------------------------
#CLI

def optimize_problem_from_excel_file(infile, outfile):
  if os.path.exists(infile):

    print(f"Loading file {infile}.")
    p1 = RetailProblem.load_from_excel(infile)

    print("Initializing optimization problem.")
    p1.initialize_optimization_problem()

    print("Attempting to solve problem.")
    p1.solve()

    if p1.model.status == 1:
      print(f"Optimal solution found. Saving results to {outfile}")
      p1.save_results_to_excel(outfile)
    else:
      print(f"WARNING: optimal solution was not found. Model status was {p1.model.status}")
      print("Please try refining your problem so a solution exists")

  else:
    print(f"Error: Input file {infile} does not exist. Exiting")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Minimize bill for online retail order, as described in Excel file.')
    parser.add_argument('-i', '--inputfile', 
      help='Name of input Excel file that specifies online retail order', required=True)
    parser.add_argument('-o', '--outputfile', 
      help='Name of output Excel file to create with problem solution', required=True)
    args = parser.parse_args()

    optimize_problem_from_excel_file(args.inputfile, args.outputfile)