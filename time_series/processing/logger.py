"""Contains the used variables and functions to provide logging functionality.

See Also
--------
`SeriesPipeline`: its `logging_file_path` of the `process` method.

"""

__author__ = "Jeroen Van Der Donckt"

import logging
import pandas as pd
import re

from ..utils.logging import logging_file_to_df

# Package specific logger
logger = logging.getLogger("feature_processing_logger")
logger.setLevel(logging.DEBUG)

# Create logger which writes WARNING messages or higher to sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.WARNING)
logger.addHandler(console)


def _parse_message(message: str) -> list:
    """Parse the message of the logged info."""
    regex = r"\[(.*?)\]"
    matches = re.findall(regex, message)
    assert len(matches) == 4
    func = matches[0]
    single_series_func = bool(matches[1].lstrip("single_series_func="))
    keys = matches[2].replace("'", "")
    duration_s = float(matches[3].rstrip(" seconds"))
    return [func, single_series_func, keys, duration_s]


def _parse_logging_execution_to_df(logging_file_path: str) -> pd.DataFrame:
    """Parse the logged messages into a dataframe that contains execution info.

    Parameters
    ----------
    logging_file_path: str
        The file path where the logged messages are stored. This is the file path that
        is passed to the `SeriesPipeline` its process method.

    Returns
    -------
    pd.DataFrame
        A DataFrame with the processor its method, keys and calculation duration.

    Note
    ----
    This function only works when the `logging_file_path` used in a
    `SeriesPipeline` its `process` method is passed.

    """
    df = logging_file_to_df(logging_file_path)
    df[["function", "single_series_func", "keys", "duration"]] = \
        list(df["message"].apply(_parse_message))
    return df.drop(columns=["name", "log_level", "message"])


def get_processor_logs(logging_file_path: str) -> pd.DataFrame:
    """Get execution (time) info for each processor of a `SeriesPipeline`.

    Parameters
    ----------
    logging_file_path: str
        The file path where the logged messages are stored. This is the file path that
        is passed to the `SeriesPipeline` its `process` method.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing each processor its duration, required keys, and whether it 
        is a `single_series_func` .

    """
    df = _parse_logging_execution_to_df(logging_file_path)
    return df
