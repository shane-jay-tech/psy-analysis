"""
Generate golden standard test data for CFA and SEM.

CFA: 4-factor, 12 items, 200 samples
SEM: 3-factor with path model, 9 items, 200 samples

Fixed seed for reproducibility.
"""

import numpy as np
import pandas as pd
import os

np.random.seed(42)

# =============================================================================
# Task 1: CFA data — 4 factors x 3 items = 12 observed variables
# =============================================================================

N = 200

# Factor correlation matrix (4x4)
# Correlations between factors: 0.3 - 0.5
factor_corr = np.array([
    [1.00, 0.40, 0.35, 0.30],
    [0.40, 1.00, 0.45, 0.35],
    [0.35, 0.45, 1.00, 0.50],
    [0.30, 0.35, 0.50, 1.00],
])

# Generate correlated latent factors via Cholesky decomposition
L = np.linalg.cholesky(factor_corr)
Z = np.random.standard_normal((N, 4))
factors = Z @ L.T  # shape (200, 4)

# Factor loadings
# F1: q1, q2, q3 — loadings 0.7, 0.80, 0.85
# F2: q4, q5, q6 — loadings 0.65, 0.75, 0.80
# F3: q7, q8, q9 — loadings 0.70, 0.78, 0.82
# F4: q10, q11, q12 — loadings 0.68, 0.73, 0.78
loadings = [
    0.70, 0.80, 0.85,   # F1
    0.65, 0.75, 0.80,   # F2
    0.70, 0.78, 0.82,   # F3
    0.68, 0.73, 0.78,   # F4
]

# Which factor each item belongs to
factor_idx = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3]

# Generate observed variables: observed = loading * factor + residual
# Residual variance = 1 - loading^2 (so total variance = 1)
observed = np.zeros((N, 12))
for i in range(12):
    lam = loadings[i]
    residual_var = 1.0 - lam ** 2
    residual = np.random.normal(0, np.sqrt(residual_var), N)
    observed[:, i] = lam * factors[:, factor_idx[i]] + residual

# Transform to Likert 1-7 scale
# Current data is ~N(0,1), transform to mean=4, sd~1.2, then round and clip
observed_likert = observed * 1.2 + 4.0
observed_likert = np.round(observed_likert).astype(int)
observed_likert = np.clip(observed_likert, 1, 7)

# Create DataFrame
cfa_columns = [f'q{i+1}' for i in range(12)]
cfa_df = pd.DataFrame(observed_likert, columns=cfa_columns)

# Save
cfa_path = r'D:\code\psy-analysis\tests\fixtures\golden_stats\psychometrics\cfa.csv'
cfa_df.to_csv(cfa_path, index=False)
print(f"CFA data saved: {cfa_path}")
print(f"  Shape: {cfa_df.shape}")
print(f"  Value range: [{cfa_df.values.min()}, {cfa_df.values.max()}]")
print(f"  Mean per item: {cfa_df.mean().values.round(2)}")
print()

# =============================================================================
# Task 2: SEM data — 3 factors, path model F1->F3, F2->F3
# =============================================================================

np.random.seed(123)

# Generate F1 and F2 as correlated exogenous factors
exo_corr = np.array([
    [1.00, 0.30],
    [0.30, 1.00],
])
L_exo = np.linalg.cholesky(exo_corr)
Z_exo = np.random.standard_normal((N, 2))
exo_factors = Z_exo @ L_exo.T  # F1, F2

F1 = exo_factors[:, 0]
F2 = exo_factors[:, 1]

# F3 = 0.4*F1 + 0.35*F2 + disturbance
# disturbance variance chosen so F3 has unit variance approximately
# Var(F3) = 0.4^2 * Var(F1) + 0.35^2 * Var(F2) + 2*0.4*0.35*Cov(F1,F2) + Var(d)
# = 0.16 + 0.1225 + 2*0.4*0.35*0.30 + Var(d)
# = 0.16 + 0.1225 + 0.084 + Var(d)
# = 0.3665 + Var(d)
# For Var(F3) ~ 1: Var(d) ~ 0.6335
disturbance_var = 0.6335
disturbance = np.random.normal(0, np.sqrt(disturbance_var), N)
F3 = 0.4 * F1 + 0.35 * F2 + disturbance

all_factors_sem = np.column_stack([F1, F2, F3])

# Loadings for SEM
# F1: x1, x2, x3 — loadings 0.75, 0.80, 0.85
# F2: x4, x5, x6 — loadings 0.70, 0.78, 0.82
# F3: y1, y2, y3 — loadings 0.72, 0.80, 0.84
sem_loadings = [
    0.75, 0.80, 0.85,  # F1
    0.70, 0.78, 0.82,  # F2
    0.72, 0.80, 0.84,  # F3
]
sem_factor_idx = [0, 0, 0, 1, 1, 1, 2, 2, 2]

# Generate observed
sem_observed = np.zeros((N, 9))
for i in range(9):
    lam = sem_loadings[i]
    residual_var = 1.0 - lam ** 2
    residual = np.random.normal(0, np.sqrt(residual_var), N)
    sem_observed[:, i] = lam * all_factors_sem[:, sem_factor_idx[i]] + residual

# Transform to Likert 1-7
sem_likert = sem_observed * 1.2 + 4.0
sem_likert = np.round(sem_likert).astype(int)
sem_likert = np.clip(sem_likert, 1, 7)

# Create DataFrame
sem_columns = ['x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'y1', 'y2', 'y3']
sem_df = pd.DataFrame(sem_likert, columns=sem_columns)

# Save
sem_path = r'D:\code\psy-analysis\tests\fixtures\golden_stats\advanced\sem.csv'
sem_df.to_csv(sem_path, index=False)
print(f"SEM data saved: {sem_path}")
print(f"  Shape: {sem_df.shape}")
print(f"  Value range: [{sem_df.values.min()}, {sem_df.values.max()}]")
print(f"  Mean per item: {sem_df.mean().values.round(2)}")
