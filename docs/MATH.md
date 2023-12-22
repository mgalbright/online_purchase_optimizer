# Detailed Math Description
In this supplemental README file, I include full details of the math formulation of 
the problem. Included for math lovers only :-)

## Details

In this problem, we consider purchasing fishing lures $L$ from online retailers $R$ . However, this is totally general, and applies to any online shopping problem. Each retailer has different prices and inventories of the lures desired by the consumer.  Each retailer also charges different prices for shipping, which may be free after a threshold on purchase total.  So the goal is decide the quantity of lures to order from each retailer to minimize total costs, by maximally taking advantage of cheapest lure prices and free shipping.

**Specification:**  

Consumer wishes to buy lure models $L = [1, 2, ... l, ...]$.  
Consumer wishes to buy $n_l$ copies of lure $l$, for integer $n_l$.  

There are retailers $R = [1, 2, ... r, ...]$.  
The price of lure $l$ from retailer $r$ is $p_{l,r}$.  
The inventory of lure $l$ at retailer $r$, i.e. the max # of units for sale, is $I_{l,r}$. 

Retailer $r$ charges a flat shipping fee of $S_r$, unless the purchase total at that retailer exceeds threshold of $T_r$ dollars and qualifies for free shipping.

**Decision to make**:  
Decide the optimal quantity (number) $q_{l,r}$ of lures $l$ to buy from retailer $r$.
Note that $q_{l,r}$ is an integer.

**Binary (indicator) variables**

We'll need to introduce an indicator variable $y_r$ to indicate if the consumer has to pay for shipping from retailer $r$.  We also introduce a large integer $M_r$ to allow us to introduce a constraint on free shipping. We'll specifiy $M_r$ later.

As it turns out, it's also helpful to introduce an indicator variable $z_r$ to indicate if nothing is ordered from retailer $r$, and a large constant $N_r > M_r$.


## Problem formulation:

We want top minimize total cost = lure cost + shipping cost, across all retailers and lures:   
$$min_{q,y,z} \sum_{r} (\sum_{l} p_{l,r} \cdot q_{l,r}) + S_r \cdot y_r$$

This is the objective function to minimize, but there are constraints that we
also must include in the problem.  Note that the objective (and constratings) are linear in the
decision variables ($q_{l,r}$ , $y_r$, $z_r$), which are integers, so this is a 
Linear Integer Program.

### Constraints:

Order quanitity non-negative. (We don't need to specify this via constraint. Instead, we set 0 as a lower bound on varaibles $q_{l,r}$ when we create them.)
$$0 \le q_{l,r}$$

Order quanitity can't exceed inventory. (We need to specify constraints to enforce this.)
$$q_{l,r} \le I_{l,r}$$

Order **at least** the desired number of lures across purchases from all retailers.  Optimizer can order more than desired if it lowers the overall bill. (Note: to disable ordering extra items, make
this a strict equality):
$$\sum_r q_{l,r} \ge n_l$$

#### Shipping:
Pay for shipping indicator $y_r$ is binary:
$$y_r \in \{0,1\}$$

Assuming you purchase **something** from a retailer, you'd have this constraint:  
If the purchase total for a retailer is less than free shipping threshold $T_r$, force the user to pay for shipping: $y_r = 1$.  If the total exceeds the threshold, do not require paying for shipping (i.e. allow $y_r = 0$).  
That logic is encoded in this constraint, which we can call $g$:
$$g = (\sum_l p_{l,r} \cdot q_{l,r}) - T_r + M_r \cdot y_r \ge 0  $$

(Details about this trick with large $M_r$ and indicator varaibles $y_r$ are in Chapter 9 of Winston's Operations Research book, on constraints in Integer programming.)  

However, we don't want to enforce that logic if you purchase nothing: no need to pay for shipping if you order nothing.

So we actually have a complex IF-THEN logic for shipping:
1. If the # of items ordered from a retailer $f > 0$, then enforce constraint $g \ge 0$, to make users pay for shipping on small orders.
2. Else, do not enforce the second constraint $g \ge 0$.

We can handle this by introducing a second set of indicator variables, $z_r$.   
$z_r = 1$ means we ordered $0$ items from a retailer r (empty order).

Full constraints are thus:
$$(\sum_l q_{l,r}) \le N_r \cdot (1-z_r)$$

$$(\sum_l p_{l,r} \cdot q_{l,r}) - T_r + M_r \cdot y_r \ge - N_r \cdot z_r$$


These constraints, plus the linear objective problem, specifiy our linear
integer program to solve.

## Math details about of If-Then logic for shipping constraints:

The online retail problem has a natural If-Then constraint:
1. If an order is not empty (has $f > 0$ items), then enforce the 'pay for shipping' constraint $g\ge0$.
1. If an order is empty (has 0 items), do not enforce that constraint.

Details about If-Then constraints come from Chapter 9 of Winston's Operations Research Book, around eq. 28-29.  They can be encoded as:
1. If inequality $f > 0$ is obeyed, then enforce constraint $g >= 0$.
1. If inequality $f > 0$ is violated, then DO NOT enforce the second constraint on g.

You can implement this with a new indicator variable z, and two constraints, written like:
$$f \le N ( 1- z)$$
$$g \ge - N z$$

This works provided you choose $N$ large enough so $f \le N$ and $-g \le N$.

Interpretation: We see if $f>0$, the first constraint forces $z=0$. (Otherwise, $z=1$ would violate the first constraint.) But then $z=0$ activates the second constraint 
$g \ge 0$ . On the other hand, if $f<0$, then $z$ could be $0$ or $1$; the optimizer will chose $z=1$ to minimize shipping prices, since $z=1$ deactivates the second constraint that enforces payment for shipping.



## More math details about choosing constants $M_r$ and $N_r$

### Picking $M_r$
Recall the original shipping constraint:
$$(\sum_l p_{l,r} \cdot q_{l,r}) - T_r + M_r \cdot y_r \ge 0$$

For this constraint to work correctly, we need to define the constant $M_r$ such that
$$T_r  - (\sum_l p_{l,r} \cdot q_{l,r})  < M_r$$
for all values of $q_{l,r}$.  

Since a retail bill cannot be negative
$$\sum_l p_{l,r} \cdot q_{l,r} \ge 0$$
it follows that 
$$T_r  - (\sum_l p_{l,r} \cdot q_{l,r}) \le T_r \lt T_r + 1$$ 

Hence, a simple and safe choice would be
$$
M_r = T_r + 1
$$

### Picking $N_r$
We must also choose $N_r$ such that two inequalities always hold:
$$\sum_l q_{l,r} \le N_r$$
and
$$
 T_r - (\sum_l p_{l,r} \cdot q_{l,r}) - M_r \cdot y_r \le N_r
$$
for all values of the variables.

Note that quantities ordered must be less than inventory, so
$$
\sum_l q_{l,r} \le \sum_l I_{l,r}
$$

Hence, if $N_r$ is at least as big as $\sum_l I_{l,r}$, the first inequality always holds.

Following the logic used to compute $M_r$, if $N_r$ is at least as big as $T_r + 1$, the second inequality is also met (since $M_r y_r \ge 0$).  

Hence, a simple choice guaranteed to satisfy both restrictions simultaneously is
$$
N_r = (T_r + 1) + \sum_l I_{l,r} 
$$