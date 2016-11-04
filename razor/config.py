import os

#  All configuration requests should go through 'theConfig' object
#  It belongs to the class below.
#  It is created (in config.py) by the genconfig.py script.
#  The important requests are:
#
#  theConfig.getOccamLib()
#  theConfig.getLogfile()
#  theConfig.getLLVM(tool)
#  theConfig.getSTD(tool)
#

class cfgObj(object):

    def  __init__(self, libfile):
        self._occamlib = libfile
        self._llvm = { 'link'        : 'llvm-link'
                       , 'as'        : 'llvm-as'
                       , 'ar'        : 'llvm-ar'
                       , 'ld'        : 'llvm-ld'
                       , 'opt'       : 'opt'
                       , 'clang'     : 'clang'
                       , 'clang++'   : 'clang++'
                       , 'clang-cpp' : 'clang-cpp'
                       , 'nm'        : 'llvm-nm'
                       , 'llc'       : 'llc'
                   }

        self._std =  { 'as'          : 'as'
                       , 'ar'        : 'ar'
                       , 'nm'        : 'nm'
                       , 'ld'        : 'ld'
                       , 'clang'     : 'clang'
                       , 'clang++'   : 'clang++'
                       , 'clang-cpp' : 'clang-cpp'
                       , 'install'   : 'install'
                       , 'ranlib'    : 'ranlib'
                       , 'cp'        : 'cp'
                       , 'mv'        : 'mv'
                       , 'cpp'       : 'cpp'
                       , 'file'      : 'file'
                       , 'chmod'     : 'chmod'
                       , 'ln'        : 'ln'
                       , 'rm'        : 'rm'
                       , 'unlink'    : 'unlink'
                   }
        
        self._env = { 'clang'        :  'LLVM_CC_NAME'
                      , 'clang++'    :  'LLVM_CXX_NAME'  
                      , 'llvm-link'  :  'LLVM_LINK_NAME'    
                      , 'llvm-ar'    :  'LLVM_AR_NAME'    
                      , 'llvm-as'    :  'LLVM_AS_NAME'    
                      , 'llvm-ld'    :  'LLVM_LD_NAME'    
                      , 'llc'        :  'LLVM_LLC_NAME'    
                      , 'opt'        :  'LLVM_OPT_NAME'    
                      , 'llvm-nm'    :  'LLVM_NM_NAME'   
                      , 'clang-cpp'  :  'LLVM_CPP_NAME'  
                  }
        
    def env_version(self, name):
        env_name = None
        if name in self._env:
            env_name = os.getenv(self._env[name])
        return env_name if env_name else name

    def getOccamLib(self):
        return self._occamlib

    def getLogfile(self):
        logfile = os.getenv('OCCAM_LOGFILE')
        if not logfile:
            logfile = '/tmp/occam.log'
        return logfile

    def getStdTool(self, tool):
        candidate = tool
        if self._std.has_key(tool):
            candidate = self._std[tool]
        return self.env_version(tool)

    def getLLVMTool(self, tool):
        candidate = tool
        if self._llvm.has_key(tool):
            candidate = self._llvm[tool]
        return self.env_version(tool)



theConfig = cfgObj('/home/iam/occam/lib/libprevirt.so')

def getOccamLib():
    return theConfig.getOccamLib()

def getLogfile():
    return theConfig.getLogfile()

def getStdTool(tool):
    return theConfig.getStdTool(tool)

def getLLVMTool(tool):
    return theConfig.getLLVMTool(tool)

    
