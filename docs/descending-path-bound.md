# Updating the fixed-face descending-path bound

This is an application of an existing optimization theorem, not a claim of a new optimization algorithm. All running times below count arithmetic/oracle operations. Geometric conditioning and accuracy are retained explicitly.

Sources:

- Mustaq Ahmed and Anna Lubiw, [Shortest Descending Paths through Given Faces](https://cccg.ca/proceedings/2006/cccg10.pdf), CCCG 2006, Section 5, Theorem 8.
- Sally Dong, Yin Tat Lee, and Guanghao Ye, [A Nearly-Linear Time Algorithm for Linear Programs with Small Treewidth: A Multiscale Representation of Robust Central Path](https://arxiv.org/abs/2011.05365), 2023 full version, Theorem 1.3.

## Formulation

Let the prescribed face sequence cross k edges. Write its crossing points as p_i(lambda_i) = a_i + lambda_i(b_i-a_i), with 0 <= lambda_i <= 1. Fix p_0 = s and p_(k+1) = t. Minimize sum_i t_i subject to

    ||p_(i+1) - p_i||_2 <= t_i,
    height(p_i) >= height(p_(i+1)).

Together with the edge bounds, this describes precisely the descending polygonal paths following the prescribed sequence. Straight segments remain inside their triangular faces. There are O(k) scalar variables and constant-dimensional norm constraints. The original paper uses a generic SOCP bound O(k^3.5 log(1/epsilon)).

## A product of small convex sets

Give each segment its own endpoint-parameter copies, plus t_i. Put all its local inequalities into a convex block K_i of dimension at most three. Add one equality identifying the two copies of each nonfixed crossing parameter in adjacent blocks. These equalities are the rows of A.

Each equality uses two private coordinates, so its row is independent of all other rows. Each block touches at most two consecutive equality rows. Therefore the generalized dual graph of A, in the sense of Dong--Lee--Ye, is a subgraph of a path. A width-one tree decomposition is immediate. The total block dimension is O(k), and membership in each block takes O(1) arithmetic operations.

This is the structural reason for the improvement. Merely counting nonzeros in an SOCP would not justify nearly linear time.

## Feasibility and forced equalities

An interior-point theorem cannot be applied blindly when a descending path is forced to have equal heights. Fortunately the relevant degeneracies can be removed in linear time.

Use height variables y_i for nonhorizontal edges. Horizontal edges have fixed height but retain their independent crossing parameter. Include the fixed endpoint heights. Each y_i has an interval [l_i,u_i], and feasibility requires y_i >= y_(i+1). Define

    L_i = max_{j >= i} l_j,
    U_i = min_{j <= i} u_j.

Both sequences are nonincreasing. The height constraints are feasible exactly when L_i <= U_i for every i: necessity is immediate, and the sequence L_i itself is a feasible assignment whenever these inequalities hold.

The feasible minimum and maximum of y_i are L_i and U_i. If L_i = U_i, fix that height; for a nonhorizontal edge this fixes its crossing point as well. A horizontal edge still has a free parameter. An adjacent height constraint is universally an equality only if U_i = L_(i+1): the prefix at upper values and suffix at lower values witness the maximum possible gap. In that case feasibility forces both heights to be the same fixed constant. Delete constraints that become constants and substitute all fixed crossing parameters.

An explicit strict assignment is available without another optimization problem. For N height entries, choose strictly decreasing weights theta_i in (0,1), for example theta_i=(N+1-i)/(N+1), and set

    y_i = (1-theta_i)L_i + theta_i U_i.

Every free height lies strictly between its feasible extremes. Every nonconstant adjacent height inequality is strict: monotonicity of L,U and the strict decrease of theta imply a positive gap unless both endpoints are fixed at the same height. On every horizontal edge choose lambda_i=1/2. This gives a point strict in all remaining linear inequalities.

## Boundedness and an explicit interior radius

Choose B>0 larger than every possible individual segment length, using the bounding box of the relevant edge endpoints and s,t. Add t_i <= 2B to each block. This cannot exclude an optimum, because at the optimum t_i is its segment length, at most B. Initialize t_i=3B/2. Both the norm inequality and the upper cap have positive slack.

Every local block now has nonempty interior and bounded diameter. Compute a positive radius r by taking the minimum over all inequality slacks divided by twice a valid Lipschitz constant. For a linear inequality use its coefficient norm (or its l1 norm as an upper bound). For t_i-||p_(i+1)-p_i|| use 1+||b_i-a_i||+||b_(i+1)-a_(i+1)||, omitting fixed endpoints. Thus the ball of radius r about the assembled feasible point lies inside the product K. Its projections supply all required local initial points. This calculation is O(k).

Let R be a positive upper bound on the diameter of the full product K; for example sqrt(2k+4(k+1)B^2) is valid with normalized edge fractions. If necessary increase R so R/r >= 2. The objective vector c has norm sqrt(k+1). Zero-length or constant blocks can simply be eliminated; if no variables remain, evaluate the forced path directly.

## Running time and error

Dong--Lee--Ye Theorem 1.3 now gives an exactly feasible point, in the arithmetic/oracle model, whose objective is at most OPT + delta ||c||_2 R, in expected time

    O~( k log(R/r) log(R/(r delta)) ).

Here 0 < delta <= 1/2 and O~ hides polylogarithmic factors from the theorem. For desired additive path-length error eta>0, choose

    delta = min(1/2, eta/(sqrt(k+1) R)).

For s != t, a relative (1+epsilon) path guarantee follows by taking eta=epsilon ||s-t||, since OPT >= ||s-t||. This accounts for scale explicitly. If the resulting radius/scale ratios are polynomial in k, the usual simplified expression is expected O~(k log(1/epsilon)). On badly conditioned inputs those additional logarithms must remain; this is not a strongly polynomial or bit-complexity claim.

The algorithm optimizes only the supplied face sequence. It does not choose a globally optimal sequence on an unrestricted terrain, and the crawler does not implement this optimization algorithm.
