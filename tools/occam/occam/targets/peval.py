# ------------------------------------------------------------------------------
# OCCAM
#
# Copyright © 2011-2012, SRI International
#
#  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of SRI International nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ------------------------------------------------------------------------------

from occam.target import ArgError
from occam import target
from occam import toolchain, driver, passes
import getopt

class PartialEvalTool (target.Target):
    def opts(self, args):
        return getopt.getopt(args, 'o:', ['--log='])

    def usage(self):
        return "%s -o <output.bc> [--log <log-file>] <input.bc>" % self.name
    def desc(self):
        return '\n'.join(
            ["  partial evaluation of input.bc writing the resulting code",
             "  to output.bc."])
    def args(self):
        return [('-o', "the output file")]

    def run(self, cfg, flags, args):
        if len(args) < 1:
            raise ArgError()
        input_file = args[0]
        
        output_file = target.flag(flags, '-o')
        log_file = target.flag(flags, '--log')
        if log_file is not None:
            log_file = open(log_file, 'w+')

        return passes.peval(input_file, output_file,
                            log=log_file)

target.register('peval', PartialEvalTool('peval'))
            
