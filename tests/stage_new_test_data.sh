#!/bin/bash
# prep new test data from RRFSv2x or a retro
#
export RUN=rrfs
lookback=240   # 240h=10days
cdate=$(date -u +%Y%m%d%H)

run_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
export MY_COM_BASE=${run_dir}/my_com_base

if (( $# < 1 )); then
  echo "Usage: prep_new_test_data.sh <src_com> [cdate] [nHours]"
  echo "src_com is required, it is the com/ directory holding rrfs.PDY/ directories"
  echo "  eg,rrfsv2x: /home/role.rtrr/rrfsv2x"
  echo "     retro: /gpfs/f6/bil-fire10-oar/world-shared/jjh/rrfsv2/RRFSv2X/L60/OPSROOT/RRFSv2X.retv3/com/rrfs/v2.1.4"
  echo "cdate is the last cycle (YYYYMMDDHH, default to current datetime in UTC)"
  echo "nHours is to look back how many hours (default to 240h=10days) "
  exit
fi

src_com=$1
if (( $# >= 2)); then
  cdate=$2
fi
if (( $# >= 3)); then
  lookback=$3
fi
pdate=$(date -ud "${cdate:0:8} ${cdate:8:2} -${lookback} hours" +%Y%m%d%H)

for i in $(seq 0 ${lookback}); do
  current=$(date -ud "${pdate:0:8} ${pdate:8:2} ${i} hours" +%Y%m%d%H)
  srcdir="${src_com}/${RUN}.${current:0:8}/${current:8:2}"
  dstdir="${MY_COM_BASE}/${RUN}.${current:0:8}/${current:8:2}"
  logsrc="${src_com}/logs/${RUN}.${current:0:8}/${current:8:2}"
  logdst="${MY_COM_BASE}/logs/${RUN}.${current:0:8}/${current:8:2}"
  #
  # deterministic results
  mkdir -p "${logdst}/det"
  cd "${logdst}/det"
  cp ${logsrc}/det/*nonvar_*obs*.log .
  rmdir "${logdst}/det" 2>/dev/null  # remove the directory if empty; error out if not empty
  rmdir "${logdst}" 2>/dev/null  # remove the directory if empty; error out if not empty
  rmdir "${MY_COM_BASE}/logs/${RUN}.${current:0:8}" 2>/dev/null  # remove the directory if empty; error out if not empty

  for spinup_str in ""; do # "_spinup"; do
    echo "process JEDIVAR${spinup_str} ${current}"
    mkdir -p "${dstdir}/jedivar${spinup_str}/det"
    cd "${dstdir}/jedivar${spinup_str}/det"
    cp ${srcdir}/jedivar${spinup_str}/det/jdiag_*.nc .
    cp ${srcdir}/jedivar${spinup_str}/det/log.*out .
    cp ${srcdir}/jedivar${spinup_str}/det/jedivar.yaml .
    cp ${srcdir}/jedivar${spinup_str}/det/jedivar.pass2.yaml .
    rmdir "${dstdir}/jedivar${spinup_str}/det" 2>/dev/null  # remove the directory if empty; error out if not empty
    rmdir "${dstdir}/jedivar${spinup_str}" 2>/dev/null  # remove the directory if empty; error out if not empty

    mkdir -p "${dstdir}/nonvar_cldana/det"
    cd "${dstdir}/nonvar_cldana/det"
    cp ${srcdir}/nonvar_cldana${spinup_str}/det/stdout_cloudanalysis.d0000 stdout_cloudanalysis
    rmdir "${dstdir}/nonvar_cldana${spinup_str}/det" 2>/dev/null  # remove the directory if empty; error out if not empty
    rmdir "${dstdir}/nonvar_cldana${spinup_str}" 2>/dev/null  # remove the directory if empty; error out if not empty
  done
  cyc=10#${current:8:2}  # tmp.debug
  if (( cyc >= 3 && cyc <=8)) || (( cyc>=15 && cyc<=20)); then
    cp -rp ${dstdir}/jedivar ${dstdir}/jedivar_spinup
    cp -rp ${dstdir}/nonvar_cldana ${dstdir}/nonvar_cldana_spinup
  fi
  #
  # enkf results
  echo "process GETKF ${current}"
  mkdir -p "${dstdir}/getkf/enkf"
  for enkf_str in "getkf_observer_solver" "getkf_post"; do
    final_str="${enkf_str}"   # tmp.debug
    if [[ "${enkf_str}" == "getkf_observer_solver" ]]; then
      final_str="getkf"
    fi
    mkdir -p "${dstdir}/${final_str}/enkf"
    cd "${dstdir}/${final_str}/enkf"
    cp ${srcdir}/${enkf_str}/enkf/jdiag_*.nc .
    cp ${srcdir}/${enkf_str}/enkf/log.out .
    cp ${srcdir}/${enkf_str}/enkf/getkf.yaml .
    rmdir "${dstdir}/${final_str}/enkf" 2>/dev/null  # remove the directory if empty; error out if not empty
    rmdir "${dstdir}/${final_str}" 2>/dev/null  # remove the directory if empty; error out if not empty
  done
  for ens in $(seq -w 001 030); do
    mkdir -p "${dstdir}/nonvar_cldana/enkf/mem${ens}"
    cd "${dstdir}/nonvar_cldana/enkf/mem${ens}"
    cp ${srcdir}/nonvar_cldana/enkf/mem${ens}/stdout_cloudanalysis.d0000 stdout_cloudanalysis
    rmdir "${dstdir}/nonvar_cldana/enkf/mem${ens}" 2>/dev/null  # remove the directory if empty; error out if not empty
    rmdir "${dstdir}/nonvar_cldana/enkf" 2>/dev/null  # remove the directory if empty; error out if not empty
    rmdir "${dstdir}/nonvar_cldana" 2>/dev/null  # remove the directory if empty; error out if not empty
  done

  rmdir "${dstdir}" 2>/dev/null  # remove the directory if empty; error out if not empty
  rmdir "${MY_COM_BASE}/${RUN}.${current:0:8}" 2>/dev/null  # remove the directory if empty; error out if not empty
done
