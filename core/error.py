"""error.py."""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import loc_e, loc

from typing import TYPE_CHECKING, NoReturn
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import loc_t


class _ErrorWithLocation(Exception):
    """A parse error that can be formatted.

    Formatting is in ui.PrintError.
    """

    def __init__(self, msg, location):
        # type: (str, loc_t) -> None

        self.msg = msg

        # Ensure that the location field is always populated
        if location is None:
            self.location = loc.Missing  # type: loc_t
        else:
            self.location = location

    def HasLocation(self):
        # type: () -> bool
        return self.location.tag() != loc_e.Missing

    def UserErrorString(self):
        # type: () -> str
        return self.msg

    def __repr__(self):
        # type: () -> str
        return '<%s %r>' % (self.msg, self.location)


class Usage(_ErrorWithLocation):
    """For flag parsing errors in builtins and main()

    Called by e_usage().  TODO: Should settle on a single interface that
    can be translated.  Sometimes we use 'raise error.Usage()'
    """

    def __init__(self, msg, location):
        # type: (str, loc_t) -> None
        _ErrorWithLocation.__init__(self, msg, location)


class Runtime(Exception):
    """An error that's meant to be caught, i.e. it's non-fatal.

    Thrown by core/state.py and caught by builtins
    """

    def __init__(self, msg):
        # type: (str) -> None
        self.msg = msg

    def UserErrorString(self):
        # type: () -> str
        return self.msg


class Parse(_ErrorWithLocation):
    """Used in the parsers."""

    def __init__(self, msg, location):
        # type: (str, loc_t) -> None
        _ErrorWithLocation.__init__(self, msg, location)


class FailGlob(_ErrorWithLocation):
    """Raised when a glob matches nothing when failglob is set.

    Meant to be caught.
    """

    def __init__(self, msg, location):
        # type: (str, loc_t) -> None
        _ErrorWithLocation.__init__(self, msg, location)


class RedirectEval(_ErrorWithLocation):
    """Used in the CommandEvaluator.

    A bad redirect causes the SimpleCommand to return with status 1.  To
    make it fatal, use set -o errexit.
    """

    def __init__(self, msg, location):
        # type: (str, loc_t) -> None
        _ErrorWithLocation.__init__(self, msg, location)


class FatalRuntime(_ErrorWithLocation):
    """An exception that propagates to the top level.

    Used in the evaluators, and also also used in test builtin for
    invalid argument.
    """

    def __init__(self, exit_status, msg, location):
        # type: (int, str, loc_t) -> None
        _ErrorWithLocation.__init__(self, msg, location)
        self.exit_status = exit_status

    def ExitStatus(self):
        # type: () -> int
        return self.exit_status


class Strict(FatalRuntime):
    """Depending on shell options, these errors may be caught and ignored.

    For example, if options like these are ON:

      set -o strict_arith
      set -o strict_word_eval

    then we re-raise the error so it's caught by the top level.  Otherwise
    we catch it and return a dummy value like '' or -1 (i.e. what bash commonly
    does.)

    TODO: Have levels, like:

    OILS_STRICT_PRINT=2   # print warnings at level 2 and above
    OILS_STRICT_DIE=1  # abort the program at level 1 and above
    """

    def __init__(self, msg, location):
        # type: (str, loc_t) -> None
        FatalRuntime.__init__(self, 1, msg, location)


class ErrExit(FatalRuntime):
    """For set -e.

    Travels between WordEvaluator and CommandEvaluator.
    """

    def __init__(self, exit_status, msg, location, show_code=False):
        # type: (int, str, loc_t, bool) -> None
        FatalRuntime.__init__(self, exit_status, msg, location)
        self.show_code = show_code


class Expr(FatalRuntime):
    """e.g. KeyError, IndexError, ZeroDivisionError."""

    def __init__(self, msg, location):
        # type: (str, loc_t) -> None

        # Unique status of 3 for expression errors -- for both the caught and
        # uncaught case.
        #
        # Caught: try sets _status register to 3
        # Uncaught: shell exits with status 3
        FatalRuntime.__init__(self, 3, msg, location)


class InvalidType(Expr):
    """e.g. ~ on a bool or float, 'not' on an int."""

    def __init__(self, msg, location):
        # type: (str, loc_t) -> None
        Expr.__init__(self, msg, location)


def e_usage(msg, location):
    # type: (str, loc_t) -> NoReturn
    """Convenience wrapper for arg parsing / validation errors.

    Usually causes a builtin to fail with status 2, but the script can continue
    if 'set +o errexit'.  Main programs like bin/oil also use this.

    Caught by

    - RunAssignBuiltin and RunBuiltin, with optional LOCATION INFO
    - various main() programs, without location info

    Probably should separate these two cases?

    - builtins pass Token() or loc::Missing()
    - tool interfaces don't pass any location info
    """
    raise Usage(msg, location)


def e_strict(msg, location):
    # type: (str, loc_t) -> NoReturn
    """Convenience wrapper for strictness errors.

    Like e_die(), except the script MAY continue executing after these errors.

    TODO: This could have a level too?
    """
    raise Strict(msg, location)


def p_die(msg, location):
    # type: (str, loc_t) -> NoReturn
    """Convenience wrapper for parse errors.

    Exits with status 2.  See core/main_loop.py.
    """
    raise Parse(msg, location)


def e_die(msg, location=None):
    # type: (str, loc_t) -> NoReturn
    """Convenience wrapper for fatal runtime errors.

    Usually exits with status 1.  See osh/cmd_eval.py.
    """
    raise FatalRuntime(1, msg, location)


def e_die_status(status, msg, location=None):
    # type: (int, str, loc_t) -> NoReturn
    """Wrapper for C++ semantics.

    Note that it doesn't take positional args, so you should use %
    formatting.
    """
    raise FatalRuntime(status, msg, location)
