"""
 OCCAM

 Copyright (c) 2011-2017, SRI International

  All rights reserved.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

 * Neither the name of SRI International nor the names of its contributors may
   be used to endorse or promote products derived from this software without
   specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import os
import tempfile
import shutil

from . import config

from . import driver

from . import interface as inter

from . import stringbuffer

from . import pool

from . import utils  


def interface(input_file, output_file, wrt):
    """ computing the interfaces.
    """
    args = ['-Pinterface2', '-Pinterface2-output', output_file]
    args += driver.all_args('-Pinterface2-entry', wrt)
    return driver.previrt(input_file, '/dev/null', args)

def specialize(input_file, output_file, rewrite_file, interfaces):
    """ inter module specialization.
    """
    args = ['-Pspecialize']
    if not rewrite_file is None:
        args += ['-Pspecialize-output', rewrite_file]
    args += driver.all_args('-Pspecialize-input', interfaces)
    if output_file is None:
        output_file = '/dev/null'
    return driver.previrt(input_file, output_file, args)

def rewrite(input_file, output_file, rewrites, output=None):
    """ inter module rewriting
    """
    args = ['-Prewrite'] + driver.all_args('-Prewrite-input', rewrites)
    return driver.previrt_progress(input_file, output_file, args, output)


def internalize(input_file, output_file, interfaces, whitelist):
    """ marks unused symbols as internal/hidden
    """
    args = ['-Poccam'] + driver.all_args('-Poccam-input', interfaces)
    if whitelist is not None:
        args = args + ['-Pkeep-external', whitelist]
    return driver.previrt_progress(input_file, output_file, args)

def strip(input_file, output_file):
    """ strips unused symbols
    """
    args = [input_file, '-o', output_file]
    args += ['-strip', '-globaldce', '-globalopt', '-strip-dead-prototypes']
    return driver.run('opt', args)

def devirt(input_file, output_file):
    """ resolve indirect function calls
    """
    args = ['-devirt-ta',
            # XXX: this one is not, in general, sound
            #'-calltarget-ignore-external',
            '-inline']
    retcode = driver.previrt_progress(input_file, output_file, args)
    if retcode != 0:
        return retcode

    #FIXME: previrt_progress returns 0 in cases where --devirt-ta crashes.
    #Here we check that the output_file exists
    if not os.path.isfile(output_file):
        #Some return code different from zero
        return 3
    else:
        return retcode


def profile(input_file, output_file):
    """ count number of instructions, functions, memory accesses, etc.
    """
    args = ['-Pprofiler']
    args += ['-profile-outfile={0}'.format(output_file)]
    return driver.previrt(input_file, '/dev/null', args)

def peval(input_file, output_file, use_devirt, use_llpe, use_ipdse, log=None):
    """ intra module previrtualization
    """
    opt = tempfile.NamedTemporaryFile(suffix='.bc', delete=False)
    done = tempfile.NamedTemporaryFile(suffix='.bc', delete=False)
    tmp = tempfile.NamedTemporaryFile(suffix='.bc', delete=False)
    opt.close()
    done.close()
    tmp.close()

    #XXX: Optimize using standard llvm transformations before any other pass.
    #Otherwise, these passes will not be very effective.
    retcode = optimize(input_file, done.name)
    if retcode != 0:
        sys.stderr.write("ERROR: intra module optimization failed!\n")
        shutil.copy(input_file, output_file)
        return retcode
    else:
        sys.stderr.write("\tintra module optimization finished succesfully\n")

    if use_devirt is not None:
        retcode = devirt(done.name, tmp.name)
        if retcode != 0:
            sys.stderr.write("ERROR: resolution of indirect calls failed!\n")
            shutil.copy(done.name, output_file)
            return retcode

        sys.stderr.write("\tresolved indirect calls finished succesfully\n")
        shutil.copy(tmp.name, done.name)

    if use_llpe is not None:
        llpe_libs = []
        for lib in config.get_llpelibs():
            llpe_libs.append('-load={0}'.format(lib))
            args = llpe_libs + ['-loop-simplify', '-lcssa', \
                                '-llpe', '-llpe-omit-checks', '-llpe-single-threaded', \
                                done.name, '-o=%s' % tmp.name]
        retcode = driver.run('opt', args)
        if retcode != 0:
            sys.stderr.write("ERROR: llpe failed!\n")
            shutil.copy(done.name, output_file)
            #FIXME: unlink files
            return retcode
        else:
            sys.stderr.write("\tllpe finished succesfully\n")
        shutil.copy(tmp.name, done.name)

    if use_ipdse is not None:
        ##lower global initializers to store's in main (improve precision of sccp)
        passes = ['-lower-gv-init']
        ##dead store elimination (improve precision of sccp)
        passes += ['-memory-ssa', '-Pmem-ssa-local-mod','-Pmem-ssa-split-fields',
                   '-mem2reg', '-ip-dse', '-strip-memory-ssa-inst']
        ##perform sccp
        passes += ['-Psccp']
        ##cleanup after sccp
        passes += ['-dce', '-globaldce']
        retcode = driver.previrt(done.name, tmp.name, passes)
        if retcode != 0:
            sys.stderr.write("ERROR: ipdse failed!\n")
            shutil.copy(done.name, output_file)
            #FIXME: unlink files
            return retcode
        else:
            sys.stderr.write("\tipdse finished succesfully\n")
        shutil.copy(tmp.name, done.name)

    out = ['']
    iteration = 0
    while True:
        iteration += 1
        if iteration > 1 or \
           (use_llpe is not None or use_ipdse is not None):
            # optimize using standard llvm transformations
            retcode = optimize(done.name, opt.name)
            if retcode != 0:
                sys.stderr.write("ERROR: intra-module optimization failed!\n")
                break;
            else:
                sys.stderr.write("\tintra module optimization finished succesfully\n")
        else:
            shutil.copy(done.name, opt.name)

        # inlining using policies
        passes = ['-Ppeval']
        progress = driver.previrt_progress(opt.name, done.name, passes, output=out)
        sys.stderr.write("\tintra-module specialization finished\n")
        if progress:
            if log is not None:
                log.write(out[0])
        else:
            shutil.copy(opt.name, done.name)
            break

    shutil.copy(done.name, output_file)
    try:
        os.unlink(done.name)
        os.unlink(opt.name)
        os.unlink(tmp.name)
    except OSError:
        pass
    return retcode

def optimize(input_file, output_file):
    """ run opt -O3
    """
    args = ['-disable-simplify-libcalls', input_file, '-o', output_file, '-O3']
    return driver.run('opt', args)

def constrain_program_args(input_file, output_file, cnstrs, filename=None):
    """ constrain the program arguments.
    """
    if filename is None:
        cnstr_file = tempfile.NamedTemporaryFile(delete=False)
        cnstr_file.close()
        cnstr_file = cnstr_file.name
    else:
        cnstr_file = filename
    f = open(cnstr_file, 'w')
    (argc, argv) = cnstrs
    f.write('{0}\n'.format(argc))
    index = 0
    for x in argv:
        f.write('{0} {1}\n'.format(index, x))
        index += 1
    f.close()

    args = ['-Pconstraints', '-Pconstraints-input', cnstr_file]
    driver.previrt(input_file, output_file, args)

    if filename is None:
        os.unlink(cnstr_file)

def specialize_program_args(input_file, output_file, args, filename=None, name=None):
    """ fix the program arguments.
    """
    if filename is None:
        arg_file = tempfile.NamedTemporaryFile(delete=False)
        arg_file.close()
        arg_file = arg_file.name
    else:
        arg_file = filename
    f = open(arg_file, 'w')
    for x in args:
        f.write(x + '\n')
    f.close()

    extra_args = []
    if not name is None:
        extra_args = ['-Parguments-name', name]
    args = ['-Parguments', '-Parguments-input', arg_file] + extra_args
    driver.previrt(input_file, output_file, args)

    if filename is None:
        os.unlink(arg_file)

def deep(libs, ifaces):
    """ compute interfaces across modules.
    """
    tf = tempfile.NamedTemporaryFile(suffix='.iface', delete=False)
    tf.close()
    iface = inter.parseInterface(ifaces[0])
    for i in ifaces[1:]:
        inter.joinInterfaces(iface, inter.parseInterface(i))

    inter.writeInterface(iface, tf.name)

    progress = True
    while progress:
        progress = False
        for l in libs:
            interface(l, tf.name, [tf.name])
            x = inter.parseInterface(tf.name)
            progress = inter.joinInterfaces(iface, x) or progress
            inter.writeInterface(iface, tf.name)

    os.unlink(tf.name)
    return iface

def run_seahorn(sea_cmd, input_file, fname, is_loop_free, cpu, mem):
    """ running SeaHorn
    """
    
    def check_status(output_str):
        if "unsat" in output_str: return True
        elif "sat" in output_str: return False
        else: return None
            
    # 1. Instrument the program with assertions 
    sea_infile = tempfile.NamedTemporaryFile(suffix='.bc', delete=False)
    sea_infile.close()
    args = ['--Padd-verifier-calls',
            '--Padd-verifier-call-in-function={0}'.format(fname)]
    driver.previrt(input_file, sea_infile.name, args)
    
    # 2. Run SeaHorn
    sea_args = [  '--strip-extern'
                , '--enable-indvar'
                , '--enable-loop-idiom'
                , '--symbolize-constant-loop-bounds'
                , '--unfold-loops-for-dsa'
                , '--simplify-pointer-loops'
                , '--horn-sea-dsa-local-mod'
                , '--horn-sea-dsa-split'
                , '--dsa=sea-cs'
                , '--cpu={0}'.format(cpu)
                , '--mem={0}'.format(mem)]

    if is_loop_free:
        # the bound shouldn't affect for proving unreachability of the
        # function but we need a global bound for all loops.
        sea_args = ['bpf', '--bmc=mono', '--bound=3'] + \
                   sea_args + \
                   [   '--horn-bv-global-constraints=true'
                     , '--horn-bv-singleton-aliases=true'
                     , '--horn-bv-ignore-calloc=false'
                     , '--horn-at-most-one-predecessor']
        sys.stderr.write('\tRunning SeaHorn with BMC engine on {0} ...\n'.format(fname))        
    else:
        sea_args = ['pf'] + \
                   sea_args + \
                   [   '--horn-global-constraints=true'
                     , '--horn-singleton-aliases=true'
                     , '--horn-ignore-calloc=false'
                     , '--crab', '--crab-dom=int']
        sys.stderr.write('\tRunning SeaHorn with Spacer+AI engine on {0} ...\n'.format(fname))
    sea_args = sea_args + [sea_infile.name]
        
    sb = stringbuffer.StringBuffer()
    retcode= driver.run(sea_cmd, sea_args, sb, False)
    status = check_status(str(sb))
    if retcode == 0 and status:
        # 3. If SeaHorn proved unreachability of the function then we
        #    add assume(false) at the entry of that function.
        sys.stderr.write('SeaHorn proved unreachability of {0}!\n'.format(fname))
        sea_outfile = tempfile.NamedTemporaryFile(suffix='.bc', delete=False)
        sea_outfile.close()
        args = ['--Preplace-verifier-calls-with-unreachable']
        driver.previrt_progress(sea_infile.name, sea_outfile.name, args)
        # 4. And, we run the optimized to remove that function
        sea_opt_outfile = tempfile.NamedTemporaryFile(suffix='.bc', delete=False)
        sea_opt_outfile.close()
        optimize(sea_outfile.name, sea_opt_outfile.name)
        return sea_opt_outfile.name
    else:
        sys.stderr.write('\tSeaHorn could not prove unreachability of {0}.\n'.format(fname))
        if retcode <> 0:
            sys.stderr.write('\t\tPossibly timeout or memory limits reached\n')
        elif not status:
            sys.stderr.write('\t\tSeaHorn got a counterexample\n')
        return input_file

def precise_dce(input_file, ropfile, output_file):
    """ use SeaHorn model-checker to remove dead functions
    """
    sea_cmd = utils.get_seahorn()
    if sea_cmd is None:
        sys.stderr.write('SeaHorn not found. Aborting precise dce ...')
        shutil.copy(input_file, output_file)
        return False
        
    cost_benefit_out = tempfile.NamedTemporaryFile(delete=False)
    args  = ['--Pcost-benefit-cg']
    args += ['--Pbenefits-filename={0}'.format(ropfile)]
    args += ['--Pcost-benefit-output={0}'.format(cost_benefit_out.name)]
    driver.previrt(input_file, '/dev/null', args)

    ####
    ## TODO: make these parameters user-definable:
    ####
    benefit_threshold = 20  ## number of ROP gadgets
    cost_threshold =  3     ## number of loops
    timeout = 120           ## SeaHorn timeout in seconds
    memlimit = 4096         ## SeaHorn memory limit in MB

    seahorn_queries = []    
    for line in cost_benefit_out:
        tokens = line.split()        
        # Expected format of each token: FUNCTION BENEFIT COST
        # where FUNCTION is a string, BENEFIT is an integer, and COST is an integer
        if len(tokens) < 3:
            sys.stderr.write('ERROR: unexpected format of {0}\n'.format(cost_benefit_out.name))
            return False
        fname = tokens[0]
        fbenefit= int(tokens[1])
        fcost = int(tokens[2])
        if fbenefit >= benefit_threshold and fcost <= cost_threshold:
            seahorn_queries.extend([(fname, fcost == 0)])
    cost_benefit_out.close()

    if seahorn_queries == []:
        print "No queries for SeaHorn ..."

    #####        
    ## TODO: run SeaHorn instances in parallel
    #####
    change = False
    curfile = input_file
    for (fname, is_loop_free) in seahorn_queries:
        if fname == 'main' or \
           fname.startswith('devirt') or \
           fname.startswith('seahorn'):
            continue
        nextfile = run_seahorn(sea_cmd, curfile, fname, is_loop_free, timeout, memlimit)
        change = change | (curfile <> nextfile)
        curfile = nextfile
    shutil.copy(curfile, output_file)
    return change

