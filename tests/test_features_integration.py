"""Tests for the features functionality."""

__author__ = "Jeroen Van Der Donckt, Emiel Deprost, Jonas Van Der Donckt"

import seglearn

# import tsfresh
# import tsfel
import pytest
import pandas as pd
import numpy as np

from .utils import dummy_data
from tsflex.features import (
    MultipleFeatureDescriptors,
    FeatureCollection,
    FuncWrapper,
    feature_collection,
)
from tsflex.features.integrations import (
    seglearn_wrapper,
    tsfresh_combiner_wrapper,
    make_robust,
)


## ROBUST FUNCTIONS


def test_unrobust_gap_features(dummy_data):
    feats = MultipleFeatureDescriptors(
        functions=[np.min, np.max],
        series_names="EDA",
        windows="10s",
        strides="5s",
    )
    feature_collection = FeatureCollection(feats)

    eda_data = dummy_data["EDA"].dropna()
    eda_data[2 : 1 + 25 * 4] = None  # Leave gap of 25 s
    # -> so there are empty windows -> will rase a ValueError
    eda_data = eda_data.dropna()
    assert eda_data.isna().any() == False
    assert (eda_data.index[1:] - eda_data.index[:-1]).max() == pd.Timedelta("25 s")

    with pytest.raises(ValueError):
        feature_collection.calculate(eda_data, approve_sparsity=True, n_jobs=0)


def test_robust_gap_features(dummy_data):
    feats = MultipleFeatureDescriptors(
        # here, the 'make_robust' function is used
        functions=[make_robust(f, min_nb_samples=2) for f in [np.min, np.max]],
        series_names="EDA",
        windows="10s",
        strides="5s",
    )
    feature_collection = FeatureCollection(feats)

    eda_data = dummy_data["EDA"].dropna()
    eda_data[2 : 1 + 25 * 4] = None  # Leave gap of 25 s
    eda_data = eda_data.dropna()
    # -> so there are empty windows -> will rase a ValueError
    assert eda_data.isna().any() == False
    assert (eda_data.index[1:] - eda_data.index[:-1]).max() == pd.Timedelta("25 s")

    res_df = feature_collection.calculate(
        eda_data, return_df=True, approve_sparsity=True
    )
    assert res_df.isna()[1:4].all().all()
    assert res_df[4:].isna().any().any() == False


def test_robust_gap_features_multi_input(dummy_data):
    def abs_diff_mean(x: np.ndarray, y: np.ndarray):
        abs_diff = np.abs(x - y)
        return np.mean(abs_diff)

    feats = MultipleFeatureDescriptors(
        functions=make_robust(abs_diff_mean, min_nb_samples=2),
        series_names=("EDA", "TMP"),
        windows="10s",
        strides="5s",
    )
    feature_collection = FeatureCollection(feats)

    eda_tmp_data = dummy_data[["EDA", "TMP"]].dropna()
    eda_tmp_data[2 : 1 + 25 * 4] = None  # Leave gap of 25 s
    eda_tmp_data = eda_tmp_data.dropna()
    assert eda_tmp_data.isna().any().any() == False
    assert (eda_tmp_data.index[1:] - eda_tmp_data.index[:-1]).max() == pd.Timedelta(
        "25 s"
    )

    res_df = feature_collection.calculate(
        eda_tmp_data, return_df=True, approve_sparsity=True
    )
    assert res_df.isna()[1:4].all().all()
    assert res_df[4:].isna().any().any() == False


def test_robust_gap_features_multi_output(dummy_data):
    def mean_std(x: np.ndarray):
        return np.mean(x), np.std(x)

    feats = MultipleFeatureDescriptors(
        functions=make_robust(mean_std, min_nb_samples=2, output_names=["mean", "std"]),
        series_names="EDA",
        windows="10s",
        strides="5s",
    )
    feature_collection = FeatureCollection(feats)

    eda_data = dummy_data["EDA"].dropna()
    eda_data[2 : 1 + 25 * 4] = None  # Leave gap of 25 s
    eda_data = eda_data.dropna()
    assert eda_data.isna().any() == False
    assert (eda_data.index[1:] - eda_data.index[:-1]).max() == pd.Timedelta("25 s")

    res_df = feature_collection.calculate(
        eda_data, return_df=True, approve_sparsity=True
    )
    assert res_df.isna()[1:4].all().all()
    assert res_df[4:].isna().any().any() == False


def test_unrobust_pass_through_features(dummy_data):
    # here we set the passtrough-nans attribute to True
    feats = MultipleFeatureDescriptors(
        functions=[make_robust(f, min_nb_samples=1, passthrough_nans=True) 
                   for f in [np.mean, np.min]],
        series_names="EDA",
        windows="10s",
        strides="5s",
    )
    feature_collection = FeatureCollection(feats)

    eda_data = dummy_data["EDA"].dropna()
    eda_data[np.random.choice(dummy_data.index[1:-1], 10, replace=False)] = np.nan

    res_df = feature_collection.calculate(eda_data, return_df=True)
    assert res_df.isna().any().any()


def test_robust_pass_through_features(dummy_data):
    # here we set the passtrough-nans attribute to false
    feats = MultipleFeatureDescriptors(
        functions=[make_robust(f, passthrough_nans=False) for f in [np.mean, np.min]],
        series_names="EDA",
        windows="10s",
        strides="5s",
    )
    feature_collection = FeatureCollection(feats)

    eda_data = dummy_data["EDA"].dropna()
    eda_data[np.random.choice(dummy_data.index[1:-1], 10, replace=False)] = np.nan

    res_df = feature_collection.calculate(eda_data, return_df=True)
    assert res_df.isna().any().any() == False


## SEGLEARN


def test_seglearn_basic_features(dummy_data):
    base_features = seglearn.feature_functions.base_features

    basic_feats = MultipleFeatureDescriptors(
        functions=[seglearn_wrapper(f, k) for k, f in base_features().items()],
        series_names=["TMP", "EDA"],
        windows="5min",
        strides="2min",
    )
    feature_collection = FeatureCollection(basic_feats)

    res_df = feature_collection.calculate(dummy_data, return_df=True)
    assert res_df.shape[1] == len(base_features()) * 2
    assert res_df.shape[0] > 0
    assert res_df.isna().any().any() == False


def test_seglearn_all_features(dummy_data):
    all_features = seglearn.feature_functions.all_features

    all_feats = MultipleFeatureDescriptors(
        functions=[
            seglearn_wrapper(f, k) for k, f in all_features().items() if k != "hist4"
        ]
        + [
            seglearn_wrapper(all_features()["hist4"], [f"hist{i}" for i in range(1, 5)])
        ],
        series_names=["TMP", "EDA"],
        windows="5min",
        strides="2min",
    )
    feature_collection = FeatureCollection(all_feats)

    res_df = feature_collection.calculate(dummy_data, return_df=True)
    assert res_df.shape[1] == (len(all_features()) - 1 + 4) * 2
    assert res_df.shape[0] > 0
    assert res_df.isna().any().any() == False


## TSFRESH


def test_tsfresh_simple_features(dummy_data):
    from tsfresh.feature_extraction.feature_calculators import (
        abs_energy,
        absolute_sum_of_changes,
        cid_ce,
        variance_larger_than_standard_deviation,
    )

    simple_feats = MultipleFeatureDescriptors(
        functions=[
            abs_energy,
            absolute_sum_of_changes,
            variance_larger_than_standard_deviation,
            FuncWrapper(cid_ce, normalize=True),
        ],
        series_names=["ACC_x", "EDA"],
        windows="5min",
        strides="2min",
    )
    feature_collection = FeatureCollection(simple_feats)

    res_df = feature_collection.calculate(dummy_data, return_df=True)
    assert res_df.shape[1] == 4 * 2
    assert res_df.shape[0] > 0
    assert res_df.isna().any().any() == False


def test_tsfresh_combiner_features(dummy_data):
    from tsfresh.feature_extraction.feature_calculators import (
        index_mass_quantile,
        linear_trend,
        spkt_welch_density,
        linear_trend_timewise,
    )

    combiner_feats = MultipleFeatureDescriptors(
        functions=[
            tsfresh_combiner_wrapper(
                index_mass_quantile, param=[{"q": v} for v in [0.15, 0.5, 0.75]]
            ),
            tsfresh_combiner_wrapper(
                linear_trend,
                param=[{"attr": v} for v in ["intercept", "slope", "stderr"]],
            ),
            tsfresh_combiner_wrapper(
                spkt_welch_density, param=[{"coeff": v} for v in range(5)]
            ),
            # This function requires a pd.Series with a pd.DatetimeIndex
            tsfresh_combiner_wrapper(
                linear_trend_timewise,
                param=[{"attr": v} for v in ["intercept", "slope"]],
            ),
        ],
        series_names=["ACC_x", "EDA"],
        windows="5min",
        strides="2min",
    )
    feature_collection = FeatureCollection(combiner_feats)

    res_df = feature_collection.calculate(dummy_data, return_df=True)
    assert res_df.shape[1] == (3 + 3 + 5 + 2) * 2
    assert res_df.shape[0] > 0
    assert res_df.isna().any().any() == False


## TSFEL


def test_tsfel_basic_features(dummy_data):
    from tsfel.feature_extraction.features import (
        # Some temporal features
        autocorr,
        mean_abs_diff,
        mean_diff,
        distance,
        zero_cross,
        slope,
        abs_energy,
        pk_pk_distance,
        entropy,
        neighbourhood_peaks,
        # Some statistical features
        interq_range,
        kurtosis,
        skewness,
        calc_max,
        calc_median,
        median_abs_deviation,
        rms,
        # Some spectral features
        #  -> Almost all are "advanced" features
        wavelet_entropy,
    )

    basic_funcs = [
        # Temporal
        autocorr, mean_abs_diff, mean_diff, distance, zero_cross, slope, abs_energy, 
        pk_pk_distance, entropy, neighbourhood_peaks,
        # Statistical
        interq_range, kurtosis, skewness, calc_max, calc_median, 
        median_abs_deviation, rms,
        # Spectral
        wavelet_entropy,
    ]

    basic_feats = MultipleFeatureDescriptors(
        functions=basic_funcs,
        series_names=["ACC_x", "EDA"],
        windows="5min",
        strides="2min",
    )
    feature_collection = FeatureCollection(basic_feats)

    res_df = feature_collection.calculate(dummy_data, return_df=True)
    assert res_df.shape[1] == 18 * 2
    assert res_df.shape[0] > 0
    assert res_df.isna().any().any() == False


def test_tsfel_advanced_features(dummy_data):
    from tsfel.feature_extraction.features import (
        # Some temporal features
        calc_centroid, auc, entropy, neighbourhood_peaks,
        # Some statistical features
        hist, ecdf, ecdf_percentile_count,
        # Some spectral features
        spectral_distance, fundamental_frequency, max_power_spectrum,
        spectral_centroid, spectral_decrease, spectral_kurtosis,
        spectral_spread, human_range_energy, mfcc, fft_mean_coeff,
        wavelet_abs_mean, wavelet_std, wavelet_energy,
    )

    advanced_feats = MultipleFeatureDescriptors(
        functions=[
            # Temporal
            FuncWrapper(calc_centroid, fs=4),
            FuncWrapper(auc, fs=4),
            FuncWrapper(entropy, prob="kde", output_names="entropy_kde"),
            FuncWrapper(entropy, prob="gauss", output_names="entropy_gauss"),
            FuncWrapper(
                neighbourhood_peaks, n=5, output_names="neighbourhood_peaks_n=5"
            ),
            # Statistical
            FuncWrapper(hist, nbins=4, output_names=[f"hist{i}" for i in range(1, 5)]),
            FuncWrapper(ecdf, output_names=[f"ecdf{i}" for i in range(1, 11)]),
            FuncWrapper(ecdf_percentile_count, output_names=["ecdf_0.2", "ecdf_0.8"]),
            # Spectral
            FuncWrapper(spectral_distance, fs=4),
            FuncWrapper(fundamental_frequency, fs=4),
            FuncWrapper(max_power_spectrum, fs=4),
            FuncWrapper(spectral_centroid, fs=4),
            FuncWrapper(spectral_decrease, fs=4),
            FuncWrapper(spectral_kurtosis, fs=4),
            FuncWrapper(spectral_spread, fs=4),
            FuncWrapper(human_range_energy, fs=4),
            FuncWrapper(
                mfcc, fs=4, num_ceps=6, output_names=[f"mfcc{i}" for i in range(1, 7)]
            ),
            FuncWrapper(
                fft_mean_coeff, fs=4, nfreq=8,
                output_names=[f"fft_mean_coeff_{i}" for i in range(8)],
            ),
            FuncWrapper(
                wavelet_abs_mean,
                output_names=[f"wavelet_abs_mean_{i}" for i in range(1, 10)],
            ),
            FuncWrapper(
                wavelet_std, output_names=[f"wavelet_std_{i}" for i in range(1, 10)]
            ),
            FuncWrapper(
                wavelet_energy, widths=np.arange(1, 5),
                output_names=[f"wavelet_energy_{i}" for i in range(1, 5)],
            ),
        ],
        series_names=["ACC_x", "EDA"],
        windows="5min",
        strides="2min",
    )
    feature_collection = FeatureCollection(advanced_feats)

    res_df = feature_collection.calculate(dummy_data, return_df=True)
    assert res_df.shape[1] == (5 + 4 + 10 + 2 + 8 + 6 + 8 + 9 + 9 + 4) * 2
    assert res_df.shape[0] > 0
    assert res_df.isna().any().any() == False
