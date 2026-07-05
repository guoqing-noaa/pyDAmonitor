import os
import sys
import subprocess
from netCDF4 import Dataset
import pandas as pd


def source(bash_file, optional=False):
    """
    Source a Bash file and capture the environment variables
    """
    # check if bash_file exists
    command = f"source {bash_file} && env"
    proc = subprocess.Popen(
        ["bash", "-c", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        if optional:
            return  # do nothing for optional config files
        else:
            raise Exception(f"Error sourcing bash file: {stderr}")
    env_vars = {}
    for line in stdout.splitlines():
        key, _, value = line.partition("=")
        env_vars[key] = value
    # Update the current environment
    os.environ.update(env_vars)


def get_run_directory():
    """Get the run directory, handling both scripts and Jupyter Notebooks."""
    if "ipykernel" in sys.modules:  # Running in a Jupyter Notebook
        return os.getcwd()
    else:  # Running as a script
        return os.path.dirname(os.path.abspath(__file__))


def get_inv_bkg_ana_files(expdir, cdate):
    source(f"{expdir}/exp.setup")
    NET = os.getenv("NET")
    RUN = NET
    WGF = os.getenv("WGF")
    TAG = os.getenv("TAG")
    COMROOT = os.getenv("COMROOT")
    DATAROOT = os.getenv("DATAROOT")
    with open(f"{expdir}/VERSION", "r") as file:
        VERSION = file.readline().strip()
    # print(NET, RUN, WGF, TAG, VERSION, COMROOT, DATAROOT)

    # find the correct invariant.nc
    jedivar_log = (
        f"{COMROOT}/{NET}/{VERSION}/logs/{RUN}.{cdate[:8]}/{cdate[8:10]}/{WGF}/{RUN}_jedivar_{TAG}_{cdate}.log"
    )
    end_str = "./invariant.nc"
    with open(f"{jedivar_log}", "r") as file:
        for line in file:
            line = line.strip()
            if line.endswith(end_str):
                inv_file = line[:-len(end_str)].split(":", 1)[1].strip()[len("ln -snf"):].strip()
                break
    # print(inv_file)

    # find the background file from the prep_ic log file
    prep_ic_log = (
        f"{COMROOT}/{NET}/{VERSION}/logs/{RUN}.{cdate[:8]}/{cdate[8:10]}/{WGF}/{RUN}_prep_ic_{TAG}_{cdate}.log"
    )
    start_str = "warm start from"
    with open(f"{prep_ic_log}", "r") as file:
        for line in file:
            if line.startswith(start_str):
                bkg_file = line[len(start_str):].strip()
                break
    # print(bkg_file)

    # find the analysis file from the UMBRELLA_PREP_IC
    ana_file = f"{DATAROOT}/{cdate[:8]}/{RUN}_prep_ic_{cdate[8:10]}_{VERSION}/{WGF}/mpasin.nc"
    # print(ana_file)

    files = {
        "inv": inv_file,
        "bkg": bkg_file,
        "ana": ana_file,
    }
    return files


def load_inv_bkg_ana(files):
    datasets = {}
    datasets["inv"] = Dataset(files["inv"], "r")
    datasets["bkg"] = Dataset(files["bkg"], "r")
    datasets["ana"] = Dataset(files["ana"], "r")
    return datasets


def query_dataset(dataset, meta_exclude=None):
    if dataset.groups:
        for grp in dataset.groups:
            print(f"*{grp}")
            text = "    "
            if dataset.groups[grp].groups:
                for nestgrp in dataset.groups[grp].groups:
                    print("*" + text + nestgrp)
                    text2 = "    "
                    for var in dataset.groups[grp].groups[nestgrp].variables:
                        text2 += f"{var}, "
                    print(text + text2.rstrip(", "))
            else:
                for var in dataset.groups[grp].variables:
                    if meta_exclude is None or meta_exclude not in var:
                        text += f"{var}, "
                print(text.rstrip(", "))

    if dataset.variables:
        text = ""
        for var in dataset.variables:
            text += f"{var}, "
        print(text.rstrip(", "))


def query_data(data, meta_exclude=None):
    text = ""
    if data.data:
        data = data.data
    for var in data:
        if meta_exclude is None or meta_exclude not in var:
            text += f"{var}, "
    print(text.rstrip(", "))


def query_obj(obj):
    return [attr for attr in dir(obj) if not callable(getattr(obj, attr)) and not attr.startswith("_")]


def to_dataframe(obsDF):
    obsDF = obsDF
    if hasattr(obsDF, "data"):
        obsDF = obsDF.data
    return pd.DataFrame(obsDF)


def load_figs(*paths):
    from IPython.display import Image, display
    imgs = [Image(path) for path in paths]
    display(*imgs)


def aircraft_reject_list_to_df(filepath):
    dcReject = {}
    with open(filepath, 'r') as myfile:
        for line in myfile:
            if line.strip() and not line.strip().startswith(";"):
                fields = line.split()
                if len(fields) >= 17:
                    tailID = fields[0]  # ID?
                    if tailID in dcReject:
                        print(f"duplicate entry: {tailID}")
                    #
                    size = len(fields)
                    fail_reason = ""
                    for pos in range(17, size):
                        fail_reason = fail_reason + fields[pos]

                    dcAircraft = {
                        "tailID": fields[0],
                        "flagT": fields[1],
                        "flagW": fields[2],
                        "flagR": fields[3],
                        "FSL": fields[4],
                        "MDCRS": fields[5],
                        "N": fields[6],
                        "bs_T": fields[7],  # bs=bias
                        "std_T": fields[8],
                        "bs_S": fields[9],  # wind speed ?
                        "std_S": fields[10],
                        "bs_D": fields[11],  # wind direction?
                        "std_D": fields[12],
                        "bs_W": fields[13],
                        "std_W": fields[14],
                        "bs_RH": fields[15],
                        "std_RH": fields[16],
                        "fail_reason": fail_reason,
                    }
                    #
                    dcReject[tailID] = dcAircraft
                else:
                    print(f"warning: less than 17 columns\n{line}")
    return pd.DataFrame(dcReject).T.reset_index(drop=True)  # transpose and then drop customized row names
