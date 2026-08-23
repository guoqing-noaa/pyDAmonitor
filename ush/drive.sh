#!/usr/bin/env bash
# connect pyDAmonitor to the workflow
declare -rx PS4='+ $(basename ${BASH_SOURCE[0]:-${FUNCNAME[0]:-"Unknown"}})[${LINENO}]: '
set -x
date
#
#-----------------------------------------------------------------------
# Specify Execution Areas
#-----------------------------------------------------------------------
#
export HOMErrfs=${HOMErrfs} #comes from the workflow at runtime
export EXECrrfs=${EXECrrfs:-${HOMErrfs}/exec}
export FIXrrfs=${FIXrrfs:-${HOMErrfs}/fix}
export PARMrrfs=${PARMrrfs:-${HOMErrfs}/parm}
export USHrrfs=${USHrrfs:-${HOMErrfs}/ush}
export PYDAMONITOR=${HOMErrfs}/workflow/sideload/pyDAmonitor
#
#-----------------------------------------------------------------------
# Obtain unique process id (pid) and create the run directory (DATA).
#-----------------------------------------------------------------------
#
export MY_COM_BASE=${COMROOT}/${NET}/${rrfs_ver}
export LOG_DIR=${MY_COM_BASE}/logs/${RUN}.${PDY}/${cyc}/${WGF}
if [[ "${DO_SPINUP:-FALSE}" == "TRUE" ]];  then
  export WORKDIR=${COMOUT}/pyDAmonitor_spinup/${WGF}
  export JEDI_DIR=${COMOUT}/jedivar_spinup/${WGF}
  export NONVAR_CLD_DIR=${COMOUT}/nonvar_cldana_spinup/${WGF}
  export NONVAR_BUFR_LOG=$(ls ${LOG_DIR}/rrfs_nonvar_bufrobs_spinup_*_${CDATE}.log | head -n 1)
  export NONVAR_REFL_LOG=$(ls ${LOG_DIR}/rrfs_nonvar_reflobs_spinup_*_${CDATE}.log | head -n 1)
else
  export WORKDIR=${COMOUT}/pyDAmonitor/${WGF}
  export JEDI_DIR=${COMOUT}/jedivar/${WGF}
  export GETKF_DIR=${COMOUT}/getkf/${WGF}
  if [[ ! -d "${GETKF_DIR}" ]]; then
    export GETKF_DIR=${COMOUT}/getkf_observer/${WGF}
    if [[ ! -d "${GETKF_DIR}" ]]; then
      export GETKF_DIR=${COMOUT}/getkf_observer_solver/${WGF}
    fi
  fi
  export NONVAR_CLD_DIR=${COMOUT}/nonvar_cldana/${WGF}
  export NONVAR_BUFR_LOG=$(ls ${LOG_DIR}/rrfs_nonvar_bufrobs_*_${CDATE}.log | head -n 1)
  export NONVAR_REFL_LOG=$(ls ${LOG_DIR}/rrfs_nonvar_reflobs_*_${CDATE}.log | head -n 1)
fi
mkdir -p "${WORKDIR}"
cd "${WORKDIR}"
#
#
${PYDAMONITOR}/ush/drive_${WGF}.sh
#
#
touch pyDAmonitor.done
date
echo "pyDAmonitor HAS COMPLETED NORMALLY!"
exit 0
