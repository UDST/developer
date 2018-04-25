import numpy as np
import pandas as pd


def weighted_random_choice(df, p, target_units):
    """
    Proposal selection using weighted random choice.

    Parameters
    ----------
    df : DataFrame
        Proposals to select from
    p : Series
        Weights for each proposal
    target_units: int
        Number of units to build

    Returns
    -------
    build_idx : ndarray
        Index of buildings selected for development

    """
    # We don't know how many developments we will need, as they
    # differ in net_units. If all developments have net_units of 1
    # than we need target_units of them. So we choose the smaller
    # of available developments and target_units.
    num_to_sample = int(min(len(df.index), target_units))
    choices = np.random.choice(df.index.values,
                               size=num_to_sample,
                               replace=False, p=p)
    tot_units = df.net_units.loc[choices].values.cumsum()
    ind = int(np.searchsorted(tot_units, target_units,
                              side="left")) + 1
    return choices[:ind]


def weighted_random_choice_multiparcel(df, p, target_units):
    """
    Proposal selection using weighted random choice in the context of multiple
    proposals per parcel.

    Parameters
    ----------
    df : DataFrame
        Proposals to select from
    p : Series
        Weights for each proposal
    target_units: int
        Number of units to build

    Returns
    -------
    build_idx : ndarray
        Index of buildings selected for development

    """
    choice_idx = weighted_random_choice(df, p, target_units)
    choices = df.loc[choice_idx]
    while True:
        # If multiple proposals sampled for a given parcel, keep only one
        choice_counts = choices.parcel_id.value_counts()
        chosen_multiple = choice_counts[choice_counts > 1].index.values
        single_choices = choices[~choices.parcel_id.isin(chosen_multiple)]
        duplicate_choices = choices[choices.parcel_id.isin(chosen_multiple)]
        keep_choice = duplicate_choices.parcel_id.drop_duplicates(keep='first')
        dup_choices_to_keep = duplicate_choices.loc[keep_choice.index]
        choices = pd.concat([single_choices, dup_choices_to_keep])

        if choices.net_units.sum() >= target_units:
            break

        df = df[~df.parcel_id.isin(choices.parcel_id)]
        if len(df) == 0:
            break

        p = p.reindex(df.index)
        p = p / p.sum()
        new_target = target_units - choices.net_units.sum()
        next_choice_idx = weighted_random_choice(df, p, new_target)
        next_choices = df.loc[next_choice_idx]
        choices = pd.concat([choices, next_choices])
    return choices.index.values
