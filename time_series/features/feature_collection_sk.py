"""SKFeatureCollection class for wrapped sklearn-compatible `FeatureCollection`.

See Also
--------
Example notebooks.

"""

from __future__ import annotations  # Make typing work for the enclosing class

__author__ = "Jeroen Van Der Donckt"

import pandas as pd

from typing import List, Optional, Union
from pathlib import Path
from sklearn.base import TransformerMixin

from .feature_collection import FeatureCollection
from .feature import FeatureDescriptor, MultipleFeatureDescriptors

## Future work
# * BaseEstimator support: it is not really useful right now to support this.
#   As for example sklearn GridSearchCV requires X and y to have the same length,
#   but FeatureCalculation (almost always) transforms the length of X in your pipeline.
#   => Possible solution; look into sklearn-contrib how they handle this


class SKFeatureCollection(TransformerMixin):
    """Sklearn-compatible transformer for extracting features using a `FeatureCollection`.

    This class is basically a wrapper around `FeatureCollection` and its `calculate`
    method, enabling sklearn compatibality, e.g. including an instance of this class
    in `sklearn.pipeline.Pipeline`.

    Concretely three changes were necessary to enable this sklearn-compatibility

    1. The parameters of the `FeatureCollection` its constructor are logged in this
       class.
    2. The relevant parameters of the `FeatureCollection` its `calculate` method have
       been moved to the constructor and are also logged.
    3. The `FeatureCollection` its 'calculate' method is wrapped in this class its
       `transform` method,

    """

    def __init__(
        self,
        feature_desc_list: Union[
            List[FeatureDescriptor], List[MultipleFeatureDescriptors]
        ] = None,
        logging_file_path: Optional[Union[str, Path]] = None,
        n_jobs: Optional[int] = None,
    ):
        """Create a SKFeatureCollection.

        This constructor wraps the `FeatureCollection` constructor arguments and the
        relevant paremeters of its `calculate` method.

        Parameters
        ----------
        feature_desc_list : Union[List[Feature], List[MultipleFeatures]], optional
            Initial list of Features to add to collection, by default None
        logging_file_path: str, optional
            The file path where the logged messages are stored. If `None`, then no
            logging `FileHandler` will be used and the logging messages are only pushed
            to stdout. Otherwise, a logging `FileHandler` will write the logged messages
            to the given file path.
        n_jobs : int, optional
            The number of processes used for the feature calculation. If `None`, then
            the number returned by `os.cpu_count()` is used, by default None.
            If n_jobs is either 0 or 1, the code will be executed sequentially without
            creating a process pool. This is very useful when debugging, as the stack
            trace will be more comprehensible.

        Notes
        -----
        * If a `logging_file_path` is provided, the execution (time) statistics can be
          retrieved by calling `logger.get_function_duration_stats(logging_file_path)`
          and `logger.get_key_duration_stats(logging_file_path)`.
          Be aware that the `logging_file_path` gets cleared before the logger pushes
          logged messages. Hence, one should use a separate logging file for the
          processing and the feature part of this library.
        * It is not possible to pass the `merge_dfs` argument from the `calculate`
          method, because this should always be True (in order to output a valid
          iterable in the `transform` method)

        """
        self.feature_desc_list = feature_desc_list
        self.logging_file_path = logging_file_path
        self.n_jobs = n_jobs

    def fit(self, X=None, y=None) -> SKFeatureCollection:
        """Fit function that is not needed for this transformer.

        Note
        ----
        This function does nothing and is here for compatibility reasons.

        Parameters
        ----------
        X : Any
            Unneeded.
        y : Any
            Unneeded.

        Returns
        -------
        SKFeatureCollection
            The transformer instance itself is returned.
        """
        return self

    def transform(
        self,
        signals: Union[pd.Series, pd.DataFrame, List[Union[pd.Series, pd.DataFrame]]],
    ) -> pd.DataFrame:
        """Calculate features on the signals.

        Parameters
        ----------
        X : Union[pd.Series, pd.DataFrame, List[Union[pd.Series, pd.DataFrame]]
            Dataframe or Series list with all the required signals for the feature
            calculation.
            Note that this parameter corresponds to the `signals` parameter of the
            `FeatureCollection` its `calculate` method.

        Returns
        -------
        pd.DataFrame
            A DataFrame with the calculated features in it.

        """
        feature_collection = FeatureCollection(self.feature_desc_list)
        return feature_collection.calculate(
            signals,
            merge_dfs=True,
            show_progress=False,
            logging_file_path=self.logging_file_path,
            n_jobs=self.n_jobs,
        )
