#!/usr/bin/env bash

ROOT=`pwd`/root

# Build the manifest file
cat > nweb.manifest <<EOF
{ "modules" : ["nweb.bc"]
, "binary"  : "nweb"
, "libs"    : []
, "native_libs" : ["-lc", "-lpthread"]
, "search"  : ["/usr/lib", "/usr/local/lib", "/usr/lib/x86_64-linux-gnu/"]
, "args"    : ["8181", "${ROOT}"]
, "name"    : "nweb"
}
EOF

#make the bitcode
wllvm nweb.c -o nweb
extract-bc nweb

# Previrutalize
${OCCAM_HOME}/bin/occam previrt --work-dir=previrt nweb.manifest


# Link link the binary into the current directory
# (it was created in previrt)
#iam rm -f nweb
#iam ln -s previrt/nweb .

# Now build the non-previrt application
#iam opt -O3 nweb.bc -o nweb.opt.bc

#iam llc -filetype=obj -o nweb.opt.o nweb.opt.bc
#iam clang nweb.opt.o -o nweb-base 
