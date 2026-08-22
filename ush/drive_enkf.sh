#!/usr/bin/env bash
declare -rx PS4='+${SECONDS}s $(basename ${BASH_SOURCE[0]:-${FUNCNAME[0]:-"Unknown"}})[${LINENO}]${id}: '
set -x
#
#------------------------------------------------------------------------------------------------
# Note for offline debug: export GETKF_DIR, PYDAMONITOR, CDATE, etc
# and then run this script
#------------------------------------------------------------------------------------------------

ln -snf ${GETKF_DIR}/jdiag*.nc .
#
# plot the time series of ensemble statistics
ln -snf ${PYDAMONITOR}/scripts/timeseries_ensemble_monitor.py .
./timeseries_ensemble_monitor.py ${CDATE} 10
#
# prep files for web
ln -snf ${PYDAMONITOR}/ush/prep_web_enkf.sh .
# ./prep_web_enkf.sh  # not ready yet, to-do-item
