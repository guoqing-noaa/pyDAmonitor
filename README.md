[pyDAmonitor book](https://pyDAmonitor.github.io/docs) (showcases plots and results)

# pyDAmonitor
Safeguarding invaluable DA investments by vigilantly monitoring DA performance in both real-time and retrospective scenarios.

## Details
Data assimilation (DA) is a critical component of modern weather forecasting and earth system modeling; it enables the integration of atmospheric observations into models to increase forecast accuracy. 

pyDAmonitor automatically reads both JEDI and GSI diagnostic files to create a comprehensive set of statistics, plots, and maps of key assimilation metrics like OmB (Observation minus Background) and OmA (Observation minus Analysis), innovation distribution, etc. It aims to facilitate and speed up analysis of DA performance in both real-time and retrospective scenarios.

[pyDAmonitor book](https://pyDAmonitor.github.io/docs)

[Working with pyDAmonitor](https://github.com/pyDAmonitor/pyDAmonitor/wiki/work-with-pyDAmonitor)  

Check the [wiki](https://github.com/pyDAmonitor/pyDAmonitor/wiki) for more information

## Creating the `pyDAmonitor` conda environment
Run the following commands to create and activate the `pyDAmonitor` conda environment as needed:
```
git clone https://github.com/pyDAmonitor/pyDAmonitor.git
conda env create -f pyDAmonitor/environment.yaml
conda activate pyDAmonitor
```

**Note:** The `pyDAmonitor` environment is already installed on `Hera/Ursa/Gaea/Orion/Hercules/Derecho` and can be loaded with
```
source pyDAmonitor/ush/load_pyDAmonitor.sh
```
Sample data is also staged on these machines for a quick start. If you need the sample data on other platforms, feel free to reach out to the pyDAmonitor team.
