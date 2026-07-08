#!/usr/bin/env python
# make histograms of OmBs and OmAs for conventional obs using jdiag files
#
from pathlib import Path
import sys
import os
import glob
import argparse
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
matplotlib.use('agg')

# Ensure the repo root (parent of scripts/) is on sys.path so `DAmonitor` can be imported
repo_root = Path(__file__).resolve().parents[1]
pyDAmonitor_ROOT = os.getenv("pyDAmonitor_ROOT")
if (repo_root / "DAmonitor").is_dir():
    sys.path.insert(0, str(repo_root))
elif pyDAmonitor_ROOT:
    sys.path.insert(0, pyDAmonitor_ROOT)
else:
    raise SystemExit("pyDAmonitor_ROOT is not set and DAmonitor was not found relative to this script. Run `source ush/load_pyDAmonitor.sh`.")
from DAmonitor.obs import obsSpace  # noqa: E402


def parse_in_args(argv):
    """
    Parse input arguments

    Parameters
    ----------
    argv : list
        Command-line arguments from sys.argv[1:]

    Returns
    -------
    Parsed input arguments

    """

    parser = argparse.ArgumentParser(description='Script that plots OmF \
                                                  histograms for conventional \
                                                  observations using jdiag \
                                                  files.')

    # Optional arguments
    parser.add_argument('--path',
                        dest='path',
                        default='.',
                        help='Path containing jdiag files',
                        type=str)

    parser.add_argument('--jdiag_file',
                        dest='jdiag_file',
                        default='ALL',
                        help='Single jdiag file to plot. Default is to plot \
                             all files',
                        type=str)

    parser.add_argument('--verbose',
                        dest='verbose',
                        default='false',
                        help='Option to print text output while code runs. \
                              Options: "true" or "false"',
                        type=str)

    return vars(parser.parse_args(argv))


def determine_jdiag_dict(path, file='ALL'):
    """
    Create a dictionary of jdiag files to plot

    Parameters
    ----------
    path : string
        Directory containing JEDI jdiag files
    file : string, optional
        File name to plot. Set to 'ALL' to plot all jdiag files

    Returns
    -------
    Dictionary containing jdiag file names organized by variable
    (t, q, etc.) and observation type

    """

    # Patterns to match
    var_patterns = ['t', 'q', 'uv', 'ps']
    num_patterns = [str(n) for n in range(100, 300)]

    # Grab all jdiag files unless files != 'ALL'
    if file == 'ALL':
        all_jdiag = glob.glob(f"{path}/jdiag_*.nc")
    else:
        all_jdiag = [f"{path}/{file}"]

    # Initialize output dictionary
    # First key corresponds to the variable
    # Second key corresponds to the obs type (3-digit prepBUFR number)
    jdiag_out = {v: {} for v in var_patterns}

    for f in all_jdiag:
        base = os.path.basename(f)
        stem, _ = os.path.splitext(base)
        sub = stem.split('_')[-1]
        if len(sub) > 3:
            v = sub[:-3]
            typ = sub[-3:]
            if (v in var_patterns) and (typ in num_patterns):
                jdiag_out[v][int(typ)] = f

    return jdiag_out


def create_omf_plots(file, plot_var, typ, verbose=False):
    """
    Create OmF histograms for a single file

    Parameters
    ----------
    file : string
        File name
    plot_var : string
        Variable included in file (e.g., t, q, etc.)
    typ : string
        Observation type in file (e.g., 120, 220, etc.)
    verbose : boolean, optional
        Option to print extra text output while code runs

    Returns
    -------
    Saves a PNG containing the O-B and O-A histogram and also returns a
    pd.DataFrame containing O-B and O-A statistics

    """

    diag = obsSpace(file)

    # These are the attributes used to extract variables
    if plot_var == 'uv':
        attrs = ['u', 'v']
    else:
        attrs = [plot_var]

    # Dictionary to append statistics to
    keys = ['var', 'type', 'omb_n', 'omb_mean', 'omb_std',
            'oma_n', 'oma_mean', 'oma_std']
    stat_dict = {k: [] for k in keys}

    # Create histogram for each attribute
    for a in attrs:
        omb = np.ma.asarray(getattr(getattr(diag, a), 'ombg')).compressed()
        oma = np.ma.asarray(getattr(getattr(diag, a), 'oman')).compressed()

        # Drop NaN/Inf values to avoid propagating invalid stats/bins
        # Copilot recommendation. I'm doubtful that we'll encounter this edge
        # case, but I see no reason to remove it
        omb = omb[np.isfinite(omb)]
        oma = oma[np.isfinite(oma)]

        if omb.size == 0 or oma.size == 0:
            if verbose:
                print(f"Skipping {a} {typ}: no valid O-B/O-A values found")
            continue

        omb_avg = np.mean(omb)
        oma_avg = np.mean(oma)
        omb_std = np.std(omb)
        oma_std = np.std(oma)

        # Save statistics to dictionary
        stat_dict['var'].append(a)
        stat_dict['type'].append(typ)
        stat_dict['omb_n'].append(omb.size)
        stat_dict['omb_mean'].append(omb_avg)
        stat_dict['omb_std'].append(omb_std)
        stat_dict['oma_n'].append(oma.size)
        stat_dict['oma_mean'].append(oma_avg)
        stat_dict['oma_std'].append(oma_std)

        # Determine bins for plotting
        max_std = max(omb_std, oma_std)
        min_avg = min(omb_avg, oma_avg)
        max_avg = max(omb_avg, oma_avg)
        min_val = min(np.amin(omb), np.amin(oma))
        max_val = max(np.amax(omb), np.amax(oma))
        dist_from_0 = max(np.abs(max(min_val, min_avg - 3*max_std)),
                          np.abs(min(max_val, max_avg + 3*max_std)))
        bins = np.linspace(-dist_from_0, dist_from_0, 25)

        if verbose:
            print(f"attr = {a}, max = {max_val}, min = {min_val}")

        # Make plot
        fig, ax = plt.subplots(nrows=1, ncols=1)
        ax.hist(omb, bins=bins, color='b', alpha=0.5, edgecolor='b', label="O$-$B")
        ax.hist(oma, bins=bins, color='r', alpha=0.5, edgecolor='r', label="O$-$A")

        # Add annotations
        fsize = 12
        ax.legend(fontsize=fsize)
        ax.set_xlabel('values', size=fsize)
        ax.set_ylabel('count', size=fsize)
        ax.set_title(f"{a} {typ}\n" +
                     f"O$-$B: n = {len(omb)}, avg = {omb_avg:.2e}, stdev = {omb_std:.2e}\n" +
                     f"O$-$A: n = {len(oma)}, avg = {oma_avg:.2e}, stdev = {oma_std:.2e}", size=fsize)
        ax.grid()

        plt.subplots_adjust(left=0.11, bottom=0.11, right=0.99, top=0.85)

        # Save plot
        out_name = f"{a}{typ}_omf_hist.png"
        if verbose:
            print(f"Saving plot to {out_name}")
        plt.savefig(out_name)
        plt.close()

    return pd.DataFrame.from_dict(stat_dict)


def omf_hist_driver(all_files, verbose=False):
    """
    Driver that loops over all jdiag files and creates histograms

    Parameters
    ----------
    all_files : dictionary
        JEDI jdiag files to plot
    verbose : boolean, optional
        Option to print extra text output as the code runs

    Returns
    -------
    pd.DataFrame containing O-B and O-A statistics for all jdiag files plotted

    """

    df_ls = []

    for v in all_files:
        for typ in all_files[v]:
            if verbose:
                print(f"\nPlotting {v} {typ}")
            df_ls.append(create_omf_plots(all_files[v][typ], v, typ, verbose=verbose))

    if not df_ls:
        raise SystemExit("No matching jdiag files found; check --path and/or \
                           --jdiag_file options.")

    return pd.concat(df_ls, ignore_index=True)

#
# ***********************************************************************
# !!  MAIN starts here !!
# ***********************************************************************


if __name__ == '__main__':

    # Read in user inputs
    param = parse_in_args(sys.argv[1:])
    verbose_str = str(param['verbose']).strip().lower()
    if verbose_str not in ('true', 'false'):
        raise SystemExit('--verbose must be "true" or "false"')
    verbose = (verbose_str == 'true')

    # Determine list of jdiag files to operate on
    jdiags = determine_jdiag_dict(param['path'], file=param['jdiag_file'])

    # Create OmF plots
    stats = omf_hist_driver(jdiags, verbose=verbose)

    # Save statistics to CSV file
    stats.to_csv('jedi_conv_omf_stats.csv', index=False)
