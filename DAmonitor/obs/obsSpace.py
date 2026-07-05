from netCDF4 import Dataset, chartostring
import numpy as np


class _ObsDF:  # DataFrame-like obs structure
    def __init__(self, data):
        self.data = data

    def __getitem__(self, key):
        return self.data[key]

    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError as e:
            raise AttributeError(f"No variable '{name}_{self.varname}' found.") from e


class obsSpace:
    def __init__(self, filepath):
        """
        Initialize an obsSpace object and load the NetCDF file.

        Parameters:
        - filepath (str): Path to the NetCDF file.
        """
        self.filepath = filepath
        self.ds = Dataset(filepath, mode='r')

        # Read the dimension
        self.nlocs = len(self.ds.dimensions['Location'])
        self.locations = self.ds.variables['Location'][:]
        if "Channel" in self.ds.dimensions:
            self.nchannels = self.ds.dimensions['Channel'].size
            self.channels = self.ds.variables['Channel'][:]

        # Discover group names
        self.groups = list(self.ds.groups.keys())

        #
        self._get_metadata()

        # Remove groups, provide direct access to varaibles, such as obsSpace.t, obsSpace.q, obsSpace.rh, obsSpace.u, obsSpace.v, etc
        for var in ["airTemperature", "windEastward", "windNorthward", "specificHumidity",  "relativeHumidity", "stationPressre",
                    "dewpointTemperature", "virtualTemperature", "sensibleTemperature",
                    "brightnessTemperature", "radiance"]:
            self._get_data_by_varname(var)

    def get_valid_subset(data, item, condition={"EffectiveQC2": 0}):
        data2 = np.array(data[item])
        key, value = next(iter(condition.items()))
        return data2[data[key] == value]

    def _get_metadata(self):
        # this is used for get metadata only
        ds = self.ds
        metadata = {}
        for var in ds.groups['MetaData'].variables:
            metadata[var] = ds.groups['MetaData'].variables[var][:]
        self.metadata = metadata

    # convert groups[].variables[] to a data dictionary
    def _get_data_by_varname(self, varname):
        ds = self.ds
        # This will get both metadata and regular data
        data = {}
        varname_found = False
        for grp in ds.groups:
            if ds.groups[grp].groups:
                for nestgrp in ds.groups[grp].groups:  # DiagnosticFlags
                    if varname in ds.groups[grp].groups[nestgrp].variables:
                        data[nestgrp] = ds.groups[grp].groups[nestgrp].variables[varname][:]
                        varname_found = True
            else:
                if grp == "MetaData":
                    for var in ds.groups['MetaData'].variables:
                        if var != "longitude_latitude_pressure":   # tmp.debug: remove this in the future
                            data[var] = ds.groups['MetaData'].variables[var][:]   # remove groups, provide direct access to metadata variables
                # Some obsSpace only has moisture obserror in RH instead of q, and some only has radiance in ObsValue instead of bt
                # Users should be aware of this and DAmonitor no longer provides implicit substitute. The following 6 lines will be removed in the future,
                # elif grp == "ObsError" and varname == "specificHumidity":
                #     data["ObsError"] = ds.groups["ObsError"].variables["relativeHumidity"][:]
                #     varname_found = True
                # elif varname == "brightnessTemperature" and (grp == "ObsValue" or grp == "ObsValueAdj") and "brightnessTemperature" in ds.groups[grp].variables:
                #     data[grp] = ds.groups[grp].variables["radiance"][:]
                #     varname_found = True
                elif varname in ds.groups[grp].variables:
                    data[grp] = ds.groups[grp].variables[varname][:]
                    varname_found = True

        for var in ds.variables:
            data[var] = ds.variables[var][:]

        # assign the data dict
        if varname_found:
            if varname == "airTemperature":
                self.t = _ObsDF(data)
            elif varname == "dewpointTemperature":
                self.td = _ObsDF(data)
            elif varname == "virtualTemperature":
                self.tv = _ObsDF(data)
            elif varname == "sensibleTemperature":
                self.ts = _ObsDF(data)
            elif varname == "windEastward":
                self.u = _ObsDF(data)
            elif varname == "windNorthward":
                self.v = _ObsDF(data)
            elif varname == "specificHumidity":
                self.q = _ObsDF(data)
            elif varname == "relativeHumidity":
                self.rh = _ObsDF(data)
            elif varname == "stationPressure":
                self.ps = _ObsDF(data)
            elif varname == "brightnessTemperature":
                self.bt = _ObsDF(data)
            elif varname == "radiance":
                self.rad = _ObsDF(data)

    def __getitem__(self, key):
        # Enable obsSpace["t"], etc
        if key in ["t", "airTemperature"]:
            return self.t
        elif key in ["td", "dewpointTemperature"]:
            return self.td
        elif key in ["tv", "virtualTemperature"]:
            return self.tv
        elif key in ["ts", "sensibleTemperature"]:
            return self.ts
        elif key in ["u", "windEastward"]:
            return self.u
        elif key in ["v", "windNorthward"]:
            return self.u
        elif key in ["q", "specificHumidity"]:
            return self.q
        elif key in ["rh", "relativeHumidity"]:
            return self.rh
        elif key in ["ps", "stationPressure"]:
            return self.ps
        elif key in ["bt", "brightnessTemperature"]:
            return self.bt
        elif key in ["rad", "radiance"]:
            return self.rad

        raise KeyError(f"Key '{key}' not found.")

    def __getattr__(self, name):
        # Enable obsSpace.t
        try:
            return self.__getitem__(name)
        except KeyError:
            raise AttributeError(f"'obsSpace' object has no attribute or variable '{name}'")


class obsSpaceGSI:
    def __init__(self, filepath):
        """
        Initialize an obsSpace object and load the NetCDF file.

        Parameters:
        - filepath (str): Path to the NetCDF file.
        - var (str): variable name, such as t, q, uv
        """
        self.filepath = filepath
        self.ds = Dataset(filepath, mode='r')

        # convert netCDF4 Variable objects to a data dictionary
        self._get_data()

    def get_valid_subset(data, item, condition={"EffectiveQC2": 0}):
        data2 = np.array(data[item])
        key, value = next(iter(condition.items()))
        return data2[data[key] == value]

    def _get_data(self):
        ds = self.ds
        # This will get both metadata and regular data
        data = {}
        for var in ds.variables:
            if var == "Station_ID" or var == "Observation_Class":
                data[var] = chartostring(ds.variables[var][:])
            elif var == "Bias_Correction_Terms":
                data["Bias_Correction_1"] = ds.variables[var][:, 0]
                data["Bias_Correction_2"] = ds.variables[var][:, 1]
                data["Bias_Correction_3"] = ds.variables[var][:, 2]
            else:
                data[var] = ds.variables[var][:]

        self.data = _ObsDF(data)

    def __getitem__(self, key):
        # Enable obsSpace["t"]
        if key in ["data"]:
            return self.data

    def __getattr__(self, name):
        # Enable obsSpace.t
        try:
            return self.__getitem__(name)
        except KeyError:
            raise AttributeError(f"'obsSpaceGSI' object has no attribute or variable '{name}'")
