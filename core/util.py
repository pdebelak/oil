#t!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
util.py - Common infrastructure.
"""
from __future__ import print_function

from mycpp import mylib


class UserExit(Exception):
    """For explicit 'exit'."""

    def __init__(self, status):
        # type: (int) -> None
        self.status = status


class HistoryError(Exception):
    def __init__(self, msg):
        # type: (str) -> None
        self.msg = msg

    def UserErrorString(self):
        # type: () -> str
        return 'history: %s' % self.msg


class _DebugFile(object):
    def __init__(self):
        # type: () -> None
        pass

    def write(self, s):
        # type: (str) -> None
        pass

    def writeln(self, s):
        # type: (str) -> None
        pass

    def isatty(self):
        # type: () -> bool
        return False


class NullDebugFile(_DebugFile):
    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        _DebugFile.__init__(self)


class DebugFile(_DebugFile):
    def __init__(self, f):
        # type: (mylib.Writer) -> None
        _DebugFile.__init__(self)
        self.f = f

    def write(self, s):
        # type: (str) -> None
        """Used by dev::Tracer and ASDL node.PrettyPrint()."""
        self.f.write(s)

    def writeln(self, s):
        # type: (str) -> None
        self.write(s + '\n')

    def isatty(self):
        # type: () -> bool
        """Used by node.PrettyPrint()."""
        return self.f.isatty()
