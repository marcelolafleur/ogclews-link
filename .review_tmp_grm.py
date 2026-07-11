import numpy as np
import types
import sys
sys.path.insert(0, "/Users/mlafleur/Projects/ogclews-link-channels")
from ogclews_link.framework import get
import ogclews_link.channels  # noqa: F401

# Simulate a fully-constructed Specifications: g_RM already length T+S
TS = 400
tG1 = 20
g_RM_full = np.full(TS, 0.03)
p = types.SimpleNamespace(alpha_RM_1=0.072, alpha_RM_T=0.072,
                          g_RM=list(g_RM_full), eta_RM=np.full((TS, 80, 7), 1.0 / (80 * 7)))
ctx = types.SimpleNamespace(og_reform=p)

print("g_RM len BEFORE channel:", len(p.g_RM))
# User passes a transition growth path of, say, 3 years
get("remittances").apply(ctx, g_rm=[0.10, 0.08, 0.05])
print("g_RM len AFTER channel:", len(p.g_RM))

# Now reproduce OG-Core get_RM's TPI indexing loop
try:
    for t in range(1, tG1):
        _ = p.g_RM[t]  # OG-Core does ((1+p.g_RM[t])/...) here
    print("get_RM loop indexing: OK (no IndexError)")
except IndexError as e:
    print("get_RM loop indexing: INDEXERROR at t where len(g_RM)=", len(p.g_RM), "->", e)
