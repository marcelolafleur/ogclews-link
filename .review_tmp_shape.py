import numpy as np

# Test fixture's eta_RM is 2D (S, J). OG-Core get_rm (SS) does eta_RM[-1, :, j].
S, J = 8, 7
eta_2d = np.full((S, J), 1.0 / (S * J))
try:
    _ = eta_2d[-1, :, 0]
    print("2D eta_RM[-1,:,0]: OK (unexpected)")
except IndexError as e:
    print("2D eta_RM[-1,:,0]: IndexError ->", e)

# TPI does eta_RM[:len_T, :, j]
len_T = 5
try:
    _ = eta_2d[:len_T, :, 0]
    print("2D eta_RM[:len_T,:,0]: shape", eta_2d[:len_T, :, 0].shape, "(silently wrong, not error)")
except IndexError as e:
    print("2D eta_RM[:len_T,:,0]: IndexError ->", e)
