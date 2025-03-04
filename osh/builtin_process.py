#!/usr/bin/env python2
"""
builtin_process.py - Builtins that deal with processes or modify process state.

This is sort of the opposite of builtin_pure.py.
"""
from __future__ import print_function

from signal import SIGCONT

from _devbuild.gen import arg_types
from _devbuild.gen.syntax_asdl import loc
from _devbuild.gen.runtime_asdl import cmd_value, wait_status, wait_status_e
from core import dev
from core import error
from core.error import e_usage, e_die_status
from core import process  # W1_OK, W1_ECHILD
from core import vm
from mycpp.mylib import log, tagswitch, print_stderr
from frontend import flag_spec
from frontend import typed_args

import posix_ as posix

from typing import TYPE_CHECKING, cast
if TYPE_CHECKING:
    from core.process import Waiter, ExternalProgram, FdState
    from core.state import Mem, SearchPath
    from core.ui import ErrorFormatter


class Jobs(vm._Builtin):
    """List jobs."""

    def __init__(self, job_list):
        # type: (process.JobList) -> None
        self.job_list = job_list

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        attrs, arg_r = flag_spec.ParseCmdVal('jobs', cmd_val)
        arg = arg_types.jobs(attrs.attrs)

        if arg.l:
            style = process.STYLE_LONG
        elif arg.p:
            style = process.STYLE_PID_ONLY
        else:
            style = process.STYLE_DEFAULT

        self.job_list.DisplayJobs(style)

        if arg.debug:
            self.job_list.DebugPrint()

        return 0


class Fg(vm._Builtin):
    """Put a job in the foreground."""

    def __init__(self, job_control, job_list, waiter):
        # type: (process.JobControl, process.JobList, Waiter) -> None
        self.job_control = job_control
        self.job_list = job_list
        self.waiter = waiter

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        pid = self.job_list.GetLastStopped()
        if pid == -1:
            log('No job to put in the foreground')
            return 1

        # TODO: Print job ID rather than the PID
        log('Continue PID %d', pid)
        # Put the job's process group back into the foreground. GiveTerminal() must
        # be called before sending SIGCONT or else the process might immediately get
        # suspsended again if it tries to read/write on the terminal.
        pgid = posix.getpgid(pid)
        self.job_control.MaybeGiveTerminal(pgid)
        posix.killpg(pgid, SIGCONT)
        return self.job_list.WhenContinued(pid, self.waiter)


class Bg(vm._Builtin):
    """Put a job in the background."""

    def __init__(self, job_list):
        # type: (process.JobList) -> None
        self.job_list = job_list

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        # How does this differ from 'fg'?  It doesn't wait and it sets controlling
        # terminal?

        raise error.Usage("isn't implemented", loc.Missing)


class Fork(vm._Builtin):
    def __init__(self, shell_ex):
        # type: (vm._Executor) -> None
        self.shell_ex = shell_ex

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_spec.ParseCmdVal('fork',
                                         cmd_val,
                                         accept_typed_args=True)

        arg, location = arg_r.Peek2()
        if arg is not None:
            e_usage('got unexpected argument %r' % arg, location)

        block = typed_args.GetOneBlock(cmd_val.typed_args)
        if block is None:
            e_usage('expected a block', loc.Missing)

        return self.shell_ex.RunBackgroundJob(block)


class ForkWait(vm._Builtin):
    def __init__(self, shell_ex):
        # type: (vm._Executor) -> None
        self.shell_ex = shell_ex

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_spec.ParseCmdVal('forkwait',
                                         cmd_val,
                                         accept_typed_args=True)
        arg, location = arg_r.Peek2()
        if arg is not None:
            e_usage('got unexpected argument %r' % arg, location)

        block = typed_args.GetOneBlock(cmd_val.typed_args)
        if block is None:
            e_usage('expected a block', loc.Missing)

        return self.shell_ex.RunSubshell(block)


class Exec(vm._Builtin):
    def __init__(self, mem, ext_prog, fd_state, search_path, errfmt):
        # type: (Mem, ExternalProgram, FdState, SearchPath, ErrorFormatter) -> None
        self.mem = mem
        self.ext_prog = ext_prog
        self.fd_state = fd_state
        self.search_path = search_path
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_spec.ParseCmdVal('exec', cmd_val)

        # Apply redirects in this shell.  # NOTE: Redirects were processed earlier.
        if arg_r.AtEnd():
            self.fd_state.MakePermanent()
            return 0

        environ = self.mem.GetExported()
        i = arg_r.i
        cmd = cmd_val.argv[i]
        argv0_path = self.search_path.CachedLookup(cmd)
        if argv0_path is None:
            e_die_status(127, 'exec: %r not found' % cmd, cmd_val.arg_locs[1])

        # shift off 'exec'
        c2 = cmd_value.Argv(cmd_val.argv[i:], cmd_val.arg_locs[i:],
                            cmd_val.typed_args)

        self.ext_prog.Exec(argv0_path, c2, environ)  # NEVER RETURNS
        # makes mypy and C++ compiler happy
        raise AssertionError('unreachable')


class Wait(vm._Builtin):
    """
  wait: wait [-n] [id ...]
      Wait for job completion and return exit status.

      Waits for each process identified by an ID, which may be a process ID or a
      job specification, and reports its termination status.  If ID is not
      given, waits for all currently active child processes, and the return
      status is zero.  If ID is a a job specification, waits for all processes
      in that job's pipeline.

      If the -n option is supplied, waits for the next job to terminate and
      returns its exit status.

      Exit Status:
      Returns the status of the last ID; fails if ID is invalid or an invalid
      option is given.
  """

    def __init__(self, waiter, job_list, mem, tracer, errfmt):
        # type: (Waiter, process.JobList, Mem, dev.Tracer, ErrorFormatter) -> None
        self.waiter = waiter
        self.job_list = job_list
        self.mem = mem
        self.tracer = tracer
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        with dev.ctx_Tracer(self.tracer, 'wait', cmd_val.argv):
            return self._Run(cmd_val)

    def _Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_spec.ParseCmdVal('wait', cmd_val)
        arg = arg_types.wait(attrs.attrs)

        job_ids, arg_locs = arg_r.Rest2()

        if arg.n:
            # Loop until there is one fewer process running, there's nothing to wait
            # for, or there's a signal
            n = self.job_list.NumRunning()
            if n == 0:
                status = 127
            else:
                target = n - 1
                status = 0
                while self.job_list.NumRunning() > target:
                    result = self.waiter.WaitForOne()
                    if result == process.W1_OK:
                        status = self.waiter.last_status
                    elif result == process.W1_ECHILD:
                        # nothing to wait for, or interrupted
                        status = 127
                        break
                    elif result >= 0:  # signal
                        status = 128 + result
                        break

            return status

        if len(job_ids) == 0:
            #log('*** wait')

            # BUG: If there is a STOPPED process, this will hang forever, because we
            # don't get ECHILD.  Not sure it matters since you can now Ctrl-C it.
            # But how to fix this?

            status = 0
            while self.job_list.NumRunning() != 0:
                result = self.waiter.WaitForOne()
                if result == process.W1_ECHILD:
                    # nothing to wait for, or interrupted.  status is 0
                    break
                elif result >= 0:  # signal
                    status = 128 + result
                    break

            return status

        # Get list of jobs.  Then we need to check if they are ALL stopped.
        # Returns the exit code of the last one on the COMMAND LINE, not the exit
        # code of last one to FINISH.
        status = 1  # error
        for i, job_id in enumerate(job_ids):
            location = arg_locs[i]

            # The % syntax is sort of like ! history sub syntax, with various queries.
            # https://stackoverflow.com/questions/35026395/bash-what-is-a-jobspec
            if job_id.startswith('%'):
                raise error.Usage(
                    "doesn't support bash-style jobspecs (got %r)" % job_id,
                    location)

            # Does it look like a PID?
            try:
                pid = int(job_id)
            except ValueError:
                raise error.Usage('expected PID or jobspec, got %r' % job_id,
                                  location)

            job = self.job_list.JobFromPid(pid)
            if job is None:
                self.errfmt.Print_("%d isn't a child of this shell" % pid,
                                   blame_loc=location)
                return 127

            wait_st = job.JobWait(self.waiter)
            UP_wait_st = wait_st
            with tagswitch(wait_st) as case:
                if case(wait_status_e.Proc):
                    wait_st = cast(wait_status.Proc, UP_wait_st)
                    status = wait_st.code

                elif case(wait_status_e.Pipeline):
                    wait_st = cast(wait_status.Pipeline, UP_wait_st)
                    # TODO: handle PIPESTATUS?  Is this right?
                    status = wait_st.codes[-1]

                elif case(wait_status_e.Cancelled):
                    wait_st = cast(wait_status.Cancelled, UP_wait_st)
                    status = 128 + wait_st.sig_num

                else:
                    raise AssertionError()

        return status


class Umask(vm._Builtin):
    def __init__(self):
        # type: () -> None
        """Dummy constructor for mycpp."""
        pass

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        argv = cmd_val.argv[1:]
        if len(argv) == 0:
            # umask() has a dumb API: you can't get it without modifying it first!
            # NOTE: dash disables interrupts around the two umask() calls, but that
            # shouldn't be a concern for us.  Signal handlers won't call umask().
            mask = posix.umask(0)
            posix.umask(mask)  #
            print('0%03o' % mask)  # octal format
            return 0

        if len(argv) == 1:
            a = argv[0]
            try:
                new_mask = int(a, 8)
            except ValueError:
                # NOTE: This also happens when we have '8' or '9' in the input.
                print_stderr(
                    "osh warning: umask with symbolic input isn't implemented")
                return 1

            posix.umask(new_mask)
            return 0

        e_usage('umask: unexpected arguments', loc.Missing)
