#!/bin/bash -x
# Make sure we exit if there is a failure
set -e

mkdir -p travis_build/occam
mkdir -p travis_build/Repositories

export OCCAM_HOME=${BUILD_HOME}/travis_build/occam

export OCCAM_LOGFILE=${BUILD_HOME}/travis_build/.occam.log

export REPOS=${BUILD_HOME}/travis_build/Repositories

## Ubuntu adds suffixes to the LLVM tools that we rely on.
#export the suffix	    
export LLVM_SUFFIX=-3.5

#run the suffix additions script
. ${BUILD_HOME}/scripts/env.sh

#now set up the environment
. ${BUILD_HOME}/.travis/bash_profile

cd ${REPOS}
git clone https://github.com/SRI-CSL/whole-program-llvm.git 
cd ${BUILD_HOME}
make 
make install 
RETURN="$?"


if [ "${RETURN}" != "0" ]; then
    echo "Building OCCAM failed!"
    exit 1
fi
