#!/bin/bash
# prep new test data using RRFSv2x or a completed retro
#
lookback=2
export WGF=det
export RUN=rrfs

run_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
pyDAmonitor_dir=${run_dir}/..
prod_dir=${run_dir}/prod
export MY_COM_BASE=${run_dir}/my_com_base

if (( $# < 1 )); then
  echo "Usage: prep_new_test_data.sh <src_dir> [cdate]"
  echo "  rrfsv2x: /home/role.rtrr/rrfsv2x "
  exit
fi

src_dir=$1
if (( $# == 2)); then
  cdate=$2
else  # if cdate is not provided, using current time (suitable for realtime runs)
  cdate=$(date -u +%Y%m%d%H)
fi
mkdir -p ${prod_dir}
source "${pyDAmonitor_dir}/ush/load_pyDAmonitor.sh"

echo -e "\n=============== $(date) ================="
mdate=$(date -ud "${cdate:0:8} ${cdate:8:2} -${lookback} hours" +%Y%m%d%H)

for i in $(seq 0 ${lookback}); do
  cd ${prod_dir}
  current=$(date -ud "${mdate:0:8} ${mdate:8:2} ${i} hours" +%Y%m%d%H)
  if [[ -f "${current}/pyDAmonitor.done" ]]; then
    echo "${current} is completed, skip"
    continue
  fi
  # cp ../yaml_peek.html .
  #
  # process current cycle
  set -x
  cur_dir="${src_dir}/${RUN}.${current:0:8}/${current:8:2}/pyDAmonitor/${WGF}"
  if [[ -f "${cur_dir}/pyDAmonitor.done" ]]; then
    echo "process ${current}"
    mkdir -p "${current}" "../my_com_base/${RUN}.${current:0:8}/${current:8:2}/pyDAmonitor"
    # link/copy data in to "${current}" and then simulate prod_dir to NCO directory structure through links
    ln -snfr "${prod_dir}/${current}" "../my_com_base/${RUN}.${current:0:8}/${current:8:2}/pyDAmonitor/${WGF}"
    cd "${current}"
    # link/copy data from ${src_dir}
    ln ${cur_dir}/jdiag.*.nc .
    cp -L ${cur_dir}/log.*out .
    cp -L ${cur_dir}/nonvar*.log .
    cp -L ${cur_dir}/stdout_cloudanalysis .
    cp -L ${cur_dir}/jedivar.yaml .
    cp -L ${cur_dir}/jedivar.pass2.yaml .
    cp ${cur_dir}/pyDAmonitor.done .
    # cp ${cur_dir}/web/*.png .  # uncomment to test the web capability
    # cp ${cur_dir}/web/*.txt .

    #
    # redo parse_jedi_log.py obs_count_timeseries.py as a safeguard
    ${pyDAmonitor_dir}/scripts/parse_jedi_log.py
    ${pyDAmonitor_dir}/scripts/obs_count_timeseries.py "${current}" 10

    #sed -e "s/2024050600/${current}/g" ../../index.html_cycle > index.html
  else
    echo "Wait for src_dir ${current} pyDAmonitor task to be completed"
  fi
done

#LATEST=$(printf "%s\n" 2* | sort | tail -1)
#sed -e "s/2024050600/${LATEST}/g" ../index.html_top > index.html

# redo timeseries under the LATEST
# cd ${prod_dir}/${LATEST}
# ${prod_dir}/../pyDAmonitor/scripts/obs_count_timeseries.py ${LATEST} 10

#cd ${prod_dir}
#git add .
#git commit -m "$(date -u +%Y%m%d_%H:%M) LATEST=${LATEST}"
#git push -u --force origin main
