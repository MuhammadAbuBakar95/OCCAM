#!/usr/bin/env bash

export OCCAM_LOGFILE=${PWD}/previrt/occam.log
export OCCAM_LOGLEVEL=INFO

make clean

mkdir previrt

LIBRARY='library'

unamestr=`uname`
if [[ "$unamestr" == 'Linux' ]]; then
   LIBRARY='library.so'
elif [[ "$unamestr" == 'Darwin' ]]; then
   LIBRARY='library.dylib'
fi


# Build the manifest file  (FIXME: dylib not good for linux)
cat > simple.manifest <<EOF
{ "modules" : ["main.o.bc", "module.o.bc"]
, "binary"  : "main"
, "libs"    : ["${LIBRARY}.bc"]
, "native_libs" : []
, "search"  : []
, "args"    : ["8181"]
, "name"    : "main"
}
EOF

#make the bitcode
CC=wllvm make 
extract-bc main.o
extract-bc module.o
extract-bc ${LIBRARY}


# Previrtualize
${OCCAM_HOME}/bin/occam previrt --work-dir=previrt simple.manifest


#debugging stuff below:
for bitcode in previrt/*.bc; do
    llvm-dis  "$bitcode" &> /dev/null
done

