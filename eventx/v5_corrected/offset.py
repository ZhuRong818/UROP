"""Exposed-only elastic-net logistic regression with a genuinely fixed offset."""

from dataclasses import dataclass

import numpy as np
from scipy.special import expit, logit
from sklearn.preprocessing import StandardScaler


def smooth_objective(beta, x, y, offset, l2):
    """Mean Bernoulli NLL plus L2; last column is the unpenalized intercept."""
    z = offset + x @ beta
    penalty = beta.copy()
    penalty[-1] = 0
    value = np.mean(np.logaddexp(0, z) - y * z) + .5 * l2 * (penalty @ penalty)
    gradient = x.T @ (expit(z) - y) / len(y) + l2 * penalty
    return float(value), gradient


def probabilities(p):
    p = np.asarray(p, dtype=np.float64)
    if p.ndim != 1 or not np.isfinite(p).all() or np.any((p <= 0) | (p >= 1)):
        raise ValueError("Base probabilities must be finite and strictly between 0 and 1")
    return p


@dataclass
class OffsetLogistic:
    l1: float = 0.0
    l2: float = .1
    tol: float = 1e-7
    max_iter: int = 20000

    def fit(self, x, y, p0, exposed):
        p0 = probabilities(p0)
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        exposed = np.asarray(exposed, dtype=bool)
        if (x.ndim != 2 or len(x) != len(p0) or y.shape != p0.shape
                or exposed.shape != p0.shape or not np.isfinite(x).all()
                or not np.isin(y, [0, 1]).all()):
            raise ValueError("Invalid or misaligned residual inputs")
        if (not np.isfinite([self.l1, self.l2, self.tol]).all()
                or min(self.l1, self.l2) < 0 or self.tol <= 0 or self.max_iter < 1):
            raise ValueError("Invalid optimizer settings")
        self.n_features_in_ = x.shape[1]
        self.n_exposed_ = int(exposed.sum())
        self.scaler_ = None
        self.coef_ = np.zeros(x.shape[1] + 1)
        self.n_iter_, self.kkt_residual_ = 0, 0.0
        if not self.n_exposed_:
            self.status_ = "no_exposure_zero_correction"
            return self
        if len(np.unique(y[exposed])) != 2:
            raise ValueError("Exposed training rows need both labels; do not silently fit a constant")
        self.scaler_ = StandardScaler().fit(x[exposed])
        design = np.column_stack([self.scaler_.transform(x[exposed]), np.ones(self.n_exposed_)])
        target, offset = y[exposed], logit(p0[exposed])
        # Global Lipschitz bound for the logistic gradient. Accelerated proximal
        # gradient solves L1 exactly via soft thresholding, not a smooth surrogate.
        step = 1 / (.25 * np.linalg.norm(design, ord=2) ** 2 / len(target) + self.l2)

        def prox(b):
            out = b.copy()
            out[:-1] = np.sign(b[:-1]) * np.maximum(np.abs(b[:-1]) - step * self.l1, 0)
            return out

        beta, accelerated, momentum = self.coef_.copy(), self.coef_.copy(), 1.0
        for iteration in range(1, self.max_iter + 1):
            _, grad = smooth_objective(accelerated, design, target, offset, self.l2)
            new = prox(accelerated - step * grad)
            _, new_grad = smooth_objective(new, design, target, offset, self.l2)
            residual = float(np.max(np.abs(new - prox(new - step * new_grad))) / step)
            if residual <= self.tol:
                self.coef_, self.n_iter_, self.kkt_residual_ = new, iteration, residual
                self.status_ = "converged"
                self.objective_ = (smooth_objective(new, design, target, offset, self.l2)[0]
                                   + self.l1 * np.abs(new[:-1]).sum())
                return self
            next_momentum = (1 + np.sqrt(1 + 4 * momentum * momentum)) / 2
            accelerated = new + ((momentum - 1) / next_momentum) * (new - beta)
            beta, momentum = new, next_momentum
        raise RuntimeError(f"Offset solver did not converge: proximal KKT residual={residual:g}")

    def correction(self, x):
        x = np.asarray(x, dtype=float)
        if x.ndim != 2 or x.shape[1] != self.n_features_in_ or not np.isfinite(x).all():
            raise ValueError("Invalid residual prediction features")
        if self.scaler_ is None:
            return np.zeros(len(x))
        return self.scaler_.transform(x) @ self.coef_[:-1] + self.coef_[-1]

    def predict(self, x, p0, exposed, kappa=1.0):
        p0 = probabilities(p0)
        exposed = np.asarray(exposed, dtype=bool)
        if exposed.shape != p0.shape or len(x) != len(p0) or not 0 <= kappa <= 1:
            raise ValueError("Invalid prediction gate, length or shrinkage")
        result = p0.copy()
        if kappa and exposed.any():
            correction = self.correction(np.asarray(x)[exposed])
            result[exposed] = expit(logit(p0[exposed]) + kappa * correction)
        # No logit/sigmoid round trip on unexposed rows: bitwise identity.
        return result
