import numpy as np
S, J = 3, 2
RM = 5.0
lam = np.array([0.4, 0.6])
om = np.array([0.5, 0.3, 0.2])


def agg(eta):
    a = 0.0
    for j in range(J):
        rm_j = (eta[:, j] * RM) / (lam[j] * om)
        a += lam[j] * np.sum(om * rm_j)
    return a


eta = np.array([[0.1, 0.2], [0.15, 0.05], [0.3, 0.2]])
print("eta sum", round(eta.sum(), 3), "-> distributed RM =", agg(eta), "(target 5)")
eta2 = eta.copy()
eta2[0, 0] = 0.2
print("eta sum", round(eta2.sum(), 3), "-> distributed RM =", round(agg(eta2), 4), "(LEAKS)")
