"""Explicit fixed-model final fit; pure inputs, never loads confirmation labels.

Production callers still require independent admission, model serialization and
one-shot orchestration. This module does not itself grant that authority.
"""

from dataclasses import dataclass

import numpy as np

from .pipeline import predict_base


@dataclass
class FinalBundle:
    residual_bundle: object
    linear_features: object
    linear_base: object
    training_ids: np.ndarray
    selection: dict

    def predict(self, ids):
        predictions = self.residual_bundle.predict(ids)
        predictions['linear'] = predict_base(
            self.linear_base, self.linear_features.transform(ids).market)
        return predictions


def fit_final(trainer, confirmation_fold, tuning_folds):
    """Tune once on permitted development, then OOF residual/full-train base fit.

    A separate trainer/index scope must omit excluded/other research scopes.
    Confirmation families are removed in their entirety, including earlier rows.
    Confirmation labels can all be NaN. No outer-fold winning parameters are reused.
    """
    parent, valid = trainer.index.split(np.arange(len(trainer.index.decision)), confirmation_fold)
    if np.intersect1d(trainer.index.family[parent], trainer.index.family[valid]).size:
        raise ValueError('Confirmation families overlap development')
    bundle, ids, _, selection = trainer.fit_outer(confirmation_fold, tuning_folds)
    features, linear = trainer.selected_base(parent, 'linear')
    final = FinalBundle(bundle, features, linear, parent, selection)
    return final, ids
