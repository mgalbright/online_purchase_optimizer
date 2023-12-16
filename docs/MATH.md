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
$$
    min_{q,y} \sum_{r}(\sum_{l} p_{l,r}\cdot q_{l,r}) + S_r \cdot y_r
$$

This is the objective function to minimize, but there are constraints that we
also must include in the problem.  Note that the objective is linear in the
decision variables ($q_{l,r}$ and $y_r$), which are integers, so this is a 
Linear Integer Program.

### Constraints:

Order quanitity non-negative. (We don't need to specify this via constraint. Instead, we set 0 as a lower bound on varaibles $q_{l,r}$ when we create them.)
$$
 0 \le q_{l,r}
$$

Order quanitity can't exceed inventory. (We need to specify constraints to enforce this.)
$$
 q_{l,r} \le I_{l,r}
$$

Order **at least** the desired number of lures across purchases from all retailers.  (Can order more than desired if it lowers the overall bill):
$$
\sum_r q_{l,r} \ge n_l
$$

#### Shipping:
Pay for shipping indicator $y_r$ is binary:
$$y_r \in \{0,1\}$$

Assuming you purchase **something** from a retailer, you'd have this constraint:  
If the purchase total for a retailer is less than free shipping threshold $T_r$, force the user to pay for shipping: $y_r = 1$.  
(Else: the constraint deactivates, so $y_r$ can be 0 or 1. However,the optimizer will select free shipping $y_r = 0$ since that reduces overall price.)  
That logic is encoded in this constraint:
$$(\sum_l p_{l,r} \cdot q_{l,r}) - T_r + M_r \cdot y_r \ge 0  $$

(Details about this trick with large $M_r$ and indicator varaibles $y_r$ are in Chapter 9 of Winston's Operations Research book, on constraints in Integer programming.)  

However, we don't want to enforce that logic if you purchase nothing: no need to pay for shipping if you order nothing.

So we actually have a complex IF-THEN logic for shipping:
1. If the # of items ordered from a retailer $f > 0$, then enforce constraint $g = (\sum_l p_{l,r} \cdot q_{l,r}) - T_r + M_r \cdot y_r \ge 0 $, to make users pay for shipping on small orders.
2. Else, do not enforce the second constraint $g \ge 0$.

We can handle this by introducing a second set of indicator variables, $z_r$.   
$z_r = 1$ means we ordered $0$ items from a retailer r (empty order).

Full constraints are thus:
$$ (\sum_l q_{l,r}) \le N_r \cdot (1-z_r) $$

$$(\sum_l p_{l,r} \cdot q_{l,r}) - T_r + M_r \cdot y_r \ge - N_r \cdot z_r  $$

Explanation:
1. If you ordered some items, LHS of top equation > 0. That forces $z_r$ = 0.  Then the second equation is enforced.
1. If you did not order any items, then $z_r$ can be 0 or 1.  That deactivates the second constraint, since the second constraint is trivially true for any $y_r$, if $z_r = 1$. So the optimizer will minimize costs by selecting $y_r = 0$.

Note:  We need to chose $N_r >> M_r$. A safe choice could be be $N_r = 3M_r$.

These constraints, plus the linear objective problem, specifiy our linear
integer program to solve.

## More math details about of If-Then logic for shipping constraints:

The online retail problem has a natural If-Then constraint:
1. If an order is not empty (has > 0 items), then enforce the 'pay for shipping' constraint.
1. If an order is empty (has 0 items), do not enforce that constraint.

Details about If-Then constraints come from Chapter 9 of Winston's Operations Research Book, around eq. 28-29.  The setup is:
1. If constraint $f > 0$ is obeyed, then enforce constraint $g >= 0$.
1. If constraint $f > 0$ is not obyed, then DO NOT enforce the second constraint.

You can impelement this with a new indicator variable z, and two constraints, written like:
$$ f \le N ( 1- z)$$
$$ g \ge - N z $$

So $z=0$ means: enforce the second constraint $ g \ge 0$, because the first constraint $f < 0$ is obeyed.

Note: if $z=1$, the second constraint is always obeyed, hence it is deactivated.

Note: you must pick N to be very large, so $N >> g$ always.  Thus, if $z=1$, $g \le - Nz$ always, so the g constraint is deactivated.  If $z=0$, you recover the original constraint $ g \le 0$.


## More math details about choosing constants $M_r$ and $N_r$
Recall the original shipping constraint:
$$(\sum_l p_{l,r} \cdot q_{l,r}) - T_r + M_r \cdot y_r \ge 0  $$

For this method to work, we need to define $M_r$ such that
$$ (\sum_l p_{l,r} \cdot q_{l,r}) - T_r  < M_r$$
for all values of $q_{l,r}$.  Usually this is done ad-hoc with a large value of $M_r$, but we can specify a more principled method.

The first key insight is that, since $T_r > 0$,
$$ \sum_l p_{l,r} \cdot q_{l,r} - T_r < \sum_l p_{l,r} \cdot q_{l,r}$$

The second insight is that the above RHS can be viewed as an inner product between vectors (over the space of L):  

$$ \sum_l p_{l,r} \cdot q_{l,r} = \bf{p}_r \cdot \bf{q}_r $$


Since $p_{l,r} \ge 0$ and $q_{l,r} \ge 0$ are never negative, we can write this as the abs. value: $|\bf{p}_r \cdot \bf{q}_r|$.  

We then apply the **Cauchy Swartz Inequality**:

$$ \sum_l p_{l,r} \cdot q_{l,r} = |\bf{p}_r \cdot \bf{q}_r| \le |\bf{p}_r| |\bf{q}_r| \le |\bf{p}_r| |\bf{I}_r|$$

The last substitution on the RHS above, from $q \rightarrow I$, comes because Lure quantities cannot exceed inventories:
$$ |q_{l,r}|^2 \le |I_{l,r}|^2 $$

Hence, if we choose:
$$ M_r = \sqrt{\sum_l (p_{l,r})^2} \cdot \sqrt{\sum_l (I_{l,r})^2} $$
We are ensured 
$$ (\sum_l p_{l,r} \cdot q_{l,r}) - T_r  < M_r$$

(Note: Above, I chose the L2 norm, but you could use any norm.)

We also need to define an $N_r$ such that
$$(\sum_l p_{l,r} \cdot q_{l,r}) - T_r + M_r \cdot y_r < N_r  $$

The left hand side is always less than $2 M_r $, so an easy way to accomplish this would be $N_r = c * M_r$, where $c \ge 2$.  For some extra safety margin, I chose $c = 3$.