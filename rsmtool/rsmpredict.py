"""
Utility to generate predictions on new data
from existing RSMTool models.

:author: Nitin Madnani (nmadnani@ets.org)
:author: Anastassia Loukina (aloukina@ets.org)
:organization: ETS
"""

#!/usr/bin/env python

import argparse
import glob
import logging
import os
import sys

from os.path import basename, dirname, exists, join, normpath, splitext

import numpy as np
import pandas as pd

from rsmtool.input import (check_main_config,
                           locate_file,
                           read_json_file,
                           rename_default_columns,
                           check_flag_column)
from rsmtool.predict import predict_with_model
from rsmtool.preprocess import (filter_on_column,
                                preprocess_feature,
                                trim)
from rsmtool.utils import LogFormatter

from skll import Learner

def compute_and_save_predictions(config_file, output_file, feats_file):
    """
    Generate predictions using the information in the config file
    and save them into the given output file.
    """

    logger = logging.getLogger(__name__)

    # read in the main config file
    config_obj = read_json_file(config_file)
    config_obj = check_main_config(config_obj, context='rsmpredict')

    # get the directory where the config file lives
    # if this is the 'expm' directory, then go
    # up one level.
    configpath = dirname(config_file)

    # get the input file containing the feature values
    # for which we want to generate the predictions
    input_features_file = locate_file(config_obj['input_features_file'], configpath)
    if not input_features_file:
        raise FileNotFoundError('Input file {} does not exist'.format(config_obj['input_features_file']))

    # get the experiment ID
    experiment_id = config_obj['experiment_id']

    # get the column name that will hold the ID
    id_column = config_obj['id_column']

    # get the column name for human score (if any)
    human_score_column = config_obj['human_score_column']

    # get the column name for second human score (if any)
    second_human_score_column = config_obj['second_human_score_column']

    # get the column name for subgroups (if any)
    subgroups = config_obj['subgroups']

    # get the column names for flag columns (if any)
    flag_column_dict = check_flag_column(config_obj)

    # get the name for the candidate_column (if any)
    candidate_column = config_obj['candidate_column']

    # get the directory of the experiment
    experiment_dir = locate_file(config_obj['experiment_dir'], configpath)
    if not experiment_dir:
        raise FileNotFoundError('The directory {} does not exist.'.format(config_obj['experiment_dir']))
    else:
        experiment_output_dir = normpath(join(experiment_dir, 'output'))
        if not exists(experiment_output_dir):
            raise FileNotFoundError('The directory {} does not contain '
                                    'the output of an rsmtool experiment.'.format(experiment_dir))

    # find all the .model files in the experiment output directory
    model_files = glob.glob(join(experiment_output_dir, '*.model'))
    if not model_files:
        raise FileNotFoundError('The directory {} does not contain any rsmtool models.'.format(experiment_output_dir))

    experiment_ids = [splitext(basename(mf))[0] for mf in model_files]
    if experiment_id not in experiment_ids:
        raise FileNotFoundError('{} does not contain a model for the experiment "{}". '                                 'The following experiments are contained in this '
                                'directory: {}'.format(experiment_output_dir,
                                                       experiment_id,
                                                       experiment_ids))

    # check that the directory contains outher required files
    required_file_types = ['feature', 'postprocessing_params']
    for file_type in required_file_types:
        expected_file_name = "{}_{}.csv".format(experiment_id, file_type)
        if not exists(join(experiment_output_dir, expected_file_name)):
            raise FileNotFoundError('{} does not contain the required file '
                                    '{} that was generated during the '
                                    'original model training'.format(experiment_output_dir,
                                                                     expected_file_name))

    # read in the given features but make sure that the
    # `id_column`, `candidate_column` and subgroups are read in as a string
    logger.info('Reading features from {}'.format(input_features_file))
    string_columns = [id_column, candidate_column] + subgroups
    converter_dict = dict([(column, str) for column in string_columns if column])

    df_input = pd.read_csv(input_features_file, converters=converter_dict)

    # make sure that the columns specified in the config file actually exist
    columns_to_check = [id_column] + subgroups + list(flag_column_dict.keys())

    # add subgroups and the flag columns to the list of columns
    # that will be added to the final file
    columns_to_copy = subgroups + list(flag_column_dict.keys())

    # human_score_column will be set to sc1 by default
    # we only raise an error if it's set to something else.
    # However, since we cannot distinguish whether the column was set
    # to sc1 by default or specified as such in the config file
    # we append it to output anyway as long as
    # it is in the input file

    if human_score_column != 'sc1' or 'sc1' in df_input.columns:
        columns_to_check.append(human_score_column)
        columns_to_copy.append('sc1')

    if candidate_column:
        columns_to_check.append(candidate_column)
        columns_to_copy.append('candidate')

    if second_human_score_column:
        columns_to_check.append(second_human_score_column)
        columns_to_copy.append('sc2')

    missing_columns = set(columns_to_check).difference(df_input.columns)
    if missing_columns:
        raise KeyError("Columns {} from the config file "
                       "do not exist in the data.".format(missing_columns))

    # rename all columns
    df_input = rename_default_columns(df_input,
                                      [],
                                      id_column,
                                      human_score_column,
                                      second_human_score_column,
                                      None,
                                      None,
                                      candidate_column=candidate_column)

    # check that the id_column contains unique values
    if df_input['spkitemid'].size != df_input['spkitemid'].unique().size:
        raise ValueError("The data contains repeated response IDs in {}. Please make sure all response IDs are unique and re-run the tool.".format(id_column))



    # now we need to pre-process these features using
    # the parameters that are already stored in the
    # _features.csv file.
    df_feature_info = pd.read_csv(join(experiment_output_dir,
                                       '{}_feature.csv'.format(experiment_id)),
                                  index_col=0)
    required_features = df_feature_info.index.tolist()

    # ensure that all the features that are needed by the model
    # are present in the input file
    input_feature_columns = [c for c in df_input if c != id_column]
    missing_features = set(required_features).difference(input_feature_columns)
    if missing_features:
        raise KeyError('{} is missing the following features: {}'.format(feats_file, missing_features))
    extra_features = set(input_feature_columns).difference(required_features + [id_column])
    if extra_features:
        logging.warning('The following extraenous features will be ignored: {}'.format(extra_features))

    # keep the required features plus the id
    features_to_keep = ['spkitemid'] + required_features

    # check if actually have the human scores for this data and add
    # sc1 to preprocessed features for consistency with other tools
    has_human_scores = 'sc1' in df_input
    if has_human_scores:
        features_to_keep.append('sc1')

    df_features = df_input[features_to_keep]

    # preprocess the feature values
    logger.info('Pre-processing input features')

    # first we need to filter out NaNs and any other
    # weird features, the same way we did for rsmtool.
    df_filtered = df_features.copy()
    df_excluded = pd.DataFrame(columns=df_filtered.columns)

    for feature_name in required_features:
        newdf, newdf_excluded = filter_on_column(df_filtered, feature_name, 'spkitemid',
                                                 exclude_zeros=False,
                                                 exclude_zero_sd=False)
        del df_filtered
        df_filtered = newdf
        df_excluded = pd.merge(df_excluded, newdf_excluded, how='outer')

    # make sure that the remaining data frame is not empty
    if len(df_filtered) == 0:
        raise ValueError("There are no responses left after "
                         "filtering out non-numeric feature values. No analysis "
                         "will be run")

    df_features = df_filtered.copy()
    df_features_preprocessed = df_features.copy()
    for feature_name in required_features:

        feature_values = df_features[feature_name].values

        feature_transformation = df_feature_info.loc[feature_name]['transform']
        feature_weight = df_feature_info.loc[feature_name]['sign']

        train_feature_mean = df_feature_info.loc[feature_name]['train_mean']
        train_feature_sd = df_feature_info.loc[feature_name]['train_sd']

        train_transformed_mean = df_feature_info.loc[feature_name]['train_transformed_mean']
        train_transformed_sd = df_feature_info.loc[feature_name]['train_transformed_sd']

        # transform the feature values and remove outliers
        df_features_preprocessed[feature_name] = preprocess_feature(feature_values,
                                                                    feature_name,
                                                                    feature_transformation,
                                                                    train_feature_mean,
                                                                    train_feature_sd,
                                                                    exclude_zero_sd=False)

        # now standardize the feature values
        df_features_preprocessed[feature_name] = (df_features_preprocessed[feature_name] - train_transformed_mean) / train_transformed_sd

        # Multiply features by weight. Within the
        # current SR timeline, the mean of the transformed train
        # feature used to standardize test features has to be
        # computed before multiplying the train feature by the weight.
        df_features_preprocessed[feature_name] = df_features_preprocessed[feature_name] * feature_weight

    # save the pre-processed features to disk if we were asked to
    if feats_file:
        logger.info('Saving pre-processed feature values to {}'.format(feats_file))

        # create any directories needed for the output file
        os.makedirs(dirname(feats_file), exist_ok=True)
        df_features_preprocessed.to_csv(feats_file, index=False)

    # now load the SKLL model to generate the predictions
    model = Learner.from_file(join(experiment_output_dir, '{}.model'.format(experiment_id)))

    # now generate the predictions for the features using this model
    logger.info('Generating predictions')
    df_predictions = predict_with_model(model, df_features_preprocessed)

    # read in the post-processing parameters from disk
    df_postproc_params = pd.read_csv(join(experiment_output_dir, '{}_postprocessing_params.csv'.format(experiment_id)))
    trim_min = df_postproc_params['trim_min'].values[0]
    trim_max = df_postproc_params['trim_max'].values[0]
    h1_mean = df_postproc_params['h1_mean'].values[0]
    h1_sd = df_postproc_params['h1_sd'].values[0]
    train_predictions_mean = df_postproc_params['train_predictions_mean'].values[0]
    train_predictions_sd = df_postproc_params['train_predictions_sd'].values[0]

    # now scale the predictions
    logger.info('Rescaling predictions')
    scaled_predictions = (df_predictions['raw'] - train_predictions_mean) / train_predictions_sd
    scaled_predictions = scaled_predictions * h1_sd + h1_mean
    df_predictions['scale'] = scaled_predictions

    # trim and round the predictions
    logger.info('Trimming and rounding predictions')
    df_predictions['raw_trim'] = trim(df_predictions['raw'], trim_min, trim_max)
    df_predictions['raw_trim_round'] = np.rint(df_predictions['raw_trim']).astype('int64')
    df_predictions['scale_trim'] = trim(df_predictions['scale'], trim_min, trim_max)
    df_predictions['scale_trim_round'] = np.rint(df_predictions['scale_trim']).astype('int64')

    # add back the columns that we were requested to copy if any
    if columns_to_copy:
        df_predictions_with_metadata = pd.merge(df_predictions,
                                                df_input[['spkitemid'] + columns_to_copy])
        assert(len(df_predictions) == len(df_predictions_with_metadata))
    else:
        df_predictions_with_metadata = df_predictions.copy()

    # create any directories needed for the output file
    os.makedirs(dirname(output_file), exist_ok=True)

    # save the predictions to disk
    logger.info('Saving predictions to {}'.format(output_file))
    df_predictions_with_metadata.to_csv(output_file, index=False)

    # save excluded responses to disk
    if not df_excluded.empty:
        excluded_output_file = '{}_excluded_responses{}'.format(*splitext(output_file))
        logger.info('Saving excluded responses to {}'.format(excluded_output_file))
        df_excluded.to_csv(excluded_output_file, index=False)


def main():

    # set up the basic logging config
    fmt = LogFormatter()
    hdlr = logging.StreamHandler(sys.stdout)
    hdlr.setFormatter(fmt)
    logging.root.addHandler(hdlr)
    logging.root.setLevel(logging.INFO)

    # get a logger
    logger = logging.getLogger(__name__)

    # set up an argument parser
    parser = argparse.ArgumentParser(prog='rsmpredict.py')

    parser.add_argument('config_file', help="The JSON config file "
                                            "needed to run rsmpredict")

    parser.add_argument('output_file', help="Output file where "
                                            "predictions will be saved")

    parser.add_argument('--features', dest='preproc_feats_file',
                        help="Output file to save the pre-processed "
                             "version of the features",
                        required=False,
                        default=None)

    # parse given command line arguments
    args = parser.parse_args()

    # convert all paths to absolute to make sure
    # all files can be found later
    config_file = os.path.abspath(args.config_file)
    output_file = os.path.abspath(args.output_file)
    preproc_feats_file = None
    if args.preproc_feats_file:
        preproc_feats_file = os.path.abspath(args.preproc_feats_file)

    # generate and save the predictions
    compute_and_save_predictions(config_file,
                                 output_file,
                                 preproc_feats_file)

if __name__ == '__main__':
    main()

