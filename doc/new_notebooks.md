# Guide to writing new IPython notebooks

`rsmtool` allows developers and users to contribute new analysis sections to `rsmtool` and `rsmeval` as *custom sections* (see report_sections.md for further information). 

When writing such notebooks, some or all of the python variables below will be available in the notebook and so can be used in the notebooks. 

- `experiment_id`: The experiment ID from the config file.

- `description`: The description string from the config file. 

- `model_name` : The name of the model from the config file. 

- `use_scaled_predictions`: A boolean variable containing the value of the setting with the same name from the config file. 

- `exclude_zero_scores`: A boolean variable containing the value of the setting with the same name from the config file.

- `length_column`: The name of the column in the training and/or test data containing response length. `None` if not specified in the config file. [`rsmtool` only]

- `second_human_score_column`: The name of the column in the test data containing the second human score. `None` if not specified in the config file.

- `groups_eval`: A list containing the names of metadata or subgroup columns as specified in the config file. 

- `df_features`: A data frame containing information about the features that were specified for model training. [`rsmtool` only]

- `features_used`: A list containing the names of all the features that are used for training the model. [`rsmtool` only]

- `df_betas`: relative and standardized coefficients (`*_betas.csv`). [`rsmtool` only]

- `df_train_orig` and `df_test_orig`: Data frames containing the original training and testing data as specified in the config file, without any changes. [`rsmtool` only]

- `df_train` and `df_test`: Data frames containing the `*_train_features.csv` and `*_test_features.csv` files respectively as explained in `doc/output_csv.md`. [`rsmtool` only]

- `df_train_preproc` and `df_test_preproc`:  Data frames containing the `*_train_preprocessed_features.csv` and `*_test_preprocessed_features.csv` files respectively as explained in `doc/output_csv.md`. [`rsmtool` only]

- `df_train_other_columns` and `df_test_other_columns`: Data frames containing the ``*_train_other_columns.csv` and `*_test_other_columns.csv` files respectively as explained in `doc/output_csv.md`. [`rsmtool`: both data frames, `rsmeval`: test data only] 

- `df_train_excluded` and `df_test_excldued`: Data frames containing the `*_train_excluded_responses.csv` and `*_test_excluded_responses.csv` files respectively as explained in `doc/output_csv.md`. [`rsmtool`: both data frames, `rsmeval`: test data only] 

- `df_train_responses_with_excluded_flags` and `df_test_responses_with_excluded flags`: Data frames containing the ``*_train_responses_with_excluded_flags.csv` and `*_test_responses_with_excluded_flags.csv` files respectively as explained in `doc/output_csv.md`. [`rsmtool`: both data frames, `rsmeval`: test data only] .

- `df_train_metadata` and `df_test_metadata`: Data frames containing the `*_train_metadata.csv` and `*_test_metadata.csv`  files respectively as explained in `doc/output_csv.md`. [`rsmtool`: both data frames, `rsmeval`: test data only] 


- `df_train_length`: A data frame containing `spkitemid` and response lengths (`length`) for the training data. These are *only* available (a) if  `length_column` was specified in the config file, (b) if no values in that column are missing and, (c) if the values in that column are not distributed with a standard deviation <= 0. [`rsmtool` only]

- `df_test_human_scores`: A data frame containing `spkitemid`, test label (`sc1`) and the second human score (`sc2`) for the test data. This frame is *only* available if `second_human_score_column` was specified in the config file. Note that the data frame will contain `NaN`s for the responses for which no numeric second human score was available or for which the second score was 0 and exclude_zero_scores was set to `True`. 

- `df_pred_preproc`: A data frame containing the `*_pred_processed.csv` file as explained in `doc/output_csv.md`.

- `df_feature_subset_specs`: a data frame containing the content of `feature_subset_file` if it was specified in config file. `None` if not specified in the config file.
[`rsmtool` only]

In addition, the following variables are also available but you should *not* re-read the files under these directories which are already available as data frames.

- `output_dir`: The output directory for the experiment that contains all the generated CSV files. 
- 
- `figure_dir`: The figure directory for the experiment that contains all the generated SVG and PNG figures.

## Notes: 

1. All of the train/test dataframes apart from `df_train_orig` and  `df_test_orig` contain the `spkitemid` column which is a unique identifier for each row (see also 3) 
2. All of the train/test data frames except the `df_*_other_columns` contain an `sc1` column which contains the human score for each responses. 
3. Note that the names of the id label and the human score column in `df_train_orig` and `df_test_orig` may be different from `spkitemid` and `sc1`. The original names for these two columns were specified in the config files.  
 
