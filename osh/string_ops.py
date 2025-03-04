"""
string_ops.py - String library functions that can be exposed with a saner syntax.

OSH:

    local y=${x//a*/b}

YSH:

    var y = x => sub('a*', 'b', :ALL)

    Pass x => sub('a*', 'b', :ALL) => var y
"""

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import loc, Token, suffix_op
from core import pyutil
from core import ui
from core.error import e_die, e_strict
from mycpp.mylib import log
from osh import glob_

import libc

from typing import List, Tuple

_ = log


def Utf8Encode(code):
    # type: (int) -> str
    """Return utf-8 encoded bytes from a unicode code point.

    Based on https://stackoverflow.com/a/23502707
    """
    num_cont_bytes = 0

    if code <= 0x7F:
        return chr(code & 0x7F)  # ASCII

    elif code <= 0x7FF:
        num_cont_bytes = 1
    elif code <= 0xFFFF:
        num_cont_bytes = 2
    elif code <= 0x10FFFF:
        num_cont_bytes = 3

    else:
        return '\xEF\xBF\xBD'  # unicode replacement character

    bytes_ = []  # type: List[int]
    for _ in xrange(num_cont_bytes):
        bytes_.append(0x80 | (code & 0x3F))
        code >>= 6

    b = (0x1E << (6 - num_cont_bytes)) | (code & (0x3F >> num_cont_bytes))
    bytes_.append(b)
    bytes_.reverse()

    # mod 256 because Python ints don't wrap around!
    tmp = [chr(b & 0xFF) for b in bytes_]
    return ''.join(tmp)


# TODO: Add details of the invalid character/byte here?

INCOMPLETE_CHAR = 'Incomplete UTF-8 character'
INVALID_CONT = 'Invalid UTF-8 continuation byte'
INVALID_START = 'Invalid start of UTF-8 character'


def _CheckContinuationByte(byte):
    # type: (str) -> None
    if (ord(byte) >> 6) != 0b10:
        e_strict(INVALID_CONT, loc.Missing)


def _Utf8CharLen(starting_byte):
    # type: (int) -> int
    if (starting_byte >> 7) == 0b0:
        return 1
    elif (starting_byte >> 5) == 0b110:
        return 2
    elif (starting_byte >> 4) == 0b1110:
        return 3
    elif (starting_byte >> 3) == 0b11110:
        return 4
    else:
        e_strict(INVALID_START, loc.Missing)


def _NextUtf8Char(s, i):
    # type: (str, int) -> int
    """Given a string and a byte offset, returns the byte position after the
    character at this position.  Usually this is the position of the next
    character, but for the last character in the string, it's the position just
    past the end of the string.

    Validates UTF-8.
    """
    n = len(s)
    assert i < n, i  # should always be in range
    byte_as_int = ord(s[i])
    length = _Utf8CharLen(byte_as_int)
    for j in xrange(i + 1, i + length):
        if j >= n:
            e_strict(INCOMPLETE_CHAR, loc.Missing)
        _CheckContinuationByte(s[j])

    return i + length


def PreviousUtf8Char(s, i):
    # type: (str, int) -> int
    """Given a string and a byte offset, returns the position of the character
    before that offset.  To start (find the first byte of the last character),
    pass len(s) for the initial value of i.

    Validates UTF-8.
    """
    # All bytes in a valid UTF-8 string have one of the following formats:
    #
    #   0xxxxxxx (1-byte char)
    #   110xxxxx (start of 2-byte char)
    #   1110xxxx (start of 3-byte char)
    #   11110xxx (start of 4-byte char)
    #   10xxxxxx (continuation byte)
    #
    # Any byte that starts with 10... MUST be a continuation byte,
    # otherwise it must be the start of a character (or just invalid
    # data).
    #
    # Walking backward, we stop at the first non-continuaton byte
    # found.  We try to interpret it as a valid UTF-8 character starting
    # byte, and check that it indicates the correct length, based on how
    # far we've moved from the original byte.  Possible problems:
    #   * byte we stopped on does not have a valid value (e.g., 11111111)
    #   * start byte indicates more or fewer continuation bytes than we've seen
    #   * no start byte at beginning of array
    #
    # Note that because we are going backward, on malformed input, we
    # won't error out in the same place as when parsing the string
    # forwards as normal.
    orig_i = i

    while i > 0:
        i -= 1
        byte_as_int = ord(s[i])
        if (byte_as_int >> 6) != 0b10:
            offset = orig_i - i
            if offset != _Utf8CharLen(byte_as_int):
                # Leaving a generic error for now, but if we want to, it's not
                # hard to calculate the position where things go wrong.  Note
                # that offset might be more than 4, for an invalid utf-8 string.
                e_strict(INVALID_START, loc.Missing)
            return i

    e_strict(INVALID_START, loc.Missing)


def CountUtf8Chars(s):
    # type: (str) -> int
    """Returns the number of utf-8 characters in the byte string 's'.

    TODO: Raise exception rather than returning a string, so we can set the exit
    code of the command to 1 ?

    $ echo ${#bad}
    Invalid utf-8 at index 3 of string 'bad': 'ab\xffd'
    $ echo $?
    1
    """
    num_chars = 0
    num_bytes = len(s)
    i = 0
    while i < num_bytes:
        i = _NextUtf8Char(s, i)
        num_chars += 1
    return num_chars


def AdvanceUtf8Chars(s, num_chars, byte_offset):
    # type: (str, int, int) -> int
    """Advance a certain number of UTF-8 chars, beginning with the given byte
    offset.  Returns a byte offset.

    If we got past the end of the string
    """
    num_bytes = len(s)
    i = byte_offset  # current byte position

    for _ in xrange(num_chars):
        # Neither bash or zsh checks out of bounds for slicing.  Either begin or
        # length.
        if i >= num_bytes:
            return i
            #raise RuntimeError('Out of bounds')

        i = _NextUtf8Char(s, i)

    return i


# Implementation without Python regex:
#
# (1) PatSub: I think we fill in GlobToExtendedRegex, then use regcomp and
# regexec.  in a loop.  fnmatch() does NOT given positions of matches.
#
# (2) Strip -- % %% # ## -
#
# a. Fast path for constant strings.
# b. Convert to POSIX extended regex, to see if it matches at ALL.  If it
# doesn't match, short circuit out?  We can't do this with fnmatch.
# c. If it does match, call fnmatch() iteratively over prefixes / suffixes.
#
# - # shortest prefix - [:1], [:2], [:3] until it matches
# - ## longest prefix - [:-1] [:-2], [:3].  Works because fnmatch does not
#                       match prefixes, it matches EXATLY.
# - % shortest suffix - [-1:] [-2:] [-3:] ...
# - %% longest suffix - [1:] [2:] [3:]
#
# See remove_pattern() in subst.c for bash, and trimsub() in eval.c for
# mksh.  Dash doesn't implement it.

# TODO:
# - Unicode support: Convert both pattern, string, and replacement to unicode,
#   then the result back at the end.
# - Compile time errors for [[:space:]] ?


def DoUnarySuffixOp(s, op_tok, arg, is_extglob):
    # type: (str, Token, str, bool) -> str
    """Helper for ${x#prefix} and family."""

    id_ = op_tok.id

    # Fast path for constant strings.
    # TODO: Should be LooksLikeExtendedGlob!
    if not is_extglob and not glob_.LooksLikeGlob(arg):
        # It doesn't look like a glob, but we glob-escaped it (e.g. [ -> \[).  So
        # reverse it.  NOTE: We also do this check in Globber.Expand().  It would
        # be nice to somehow store the original string rather than
        # escaping/unescaping.
        arg = glob_.GlobUnescape(arg)

        if id_ in (Id.VOp1_Pound, Id.VOp1_DPound):  # const prefix
            # explicit check for non-empty arg (len for mycpp)
            if len(arg) and s.startswith(arg):
                return s[len(arg):]
            else:
                return s

        elif id_ in (Id.VOp1_Percent, Id.VOp1_DPercent):  # const suffix
            # need explicit check for non-empty arg (len for mycpp)
            if len(arg) and s.endswith(arg):
                return s[:-len(arg)]
            else:
                return s

        # These operators take glob arguments, we don't implement that obscure case.
        elif id_ == Id.VOp1_Comma:  # Only lowercase the first letter
            if arg != '':
                e_die("%s can't have an argument" % ui.PrettyId(id_), op_tok)
            if len(s):
                return s[0].lower() + s[1:]
            else:
                return s

        elif id_ == Id.VOp1_DComma:
            if arg != '':
                e_die("%s can't have an argument" % ui.PrettyId(id_), op_tok)
            return s.lower()

        elif id_ == Id.VOp1_Caret:  # Only uppercase the first letter
            if arg != '':
                e_die("%s can't have an argument" % ui.PrettyId(id_), op_tok)
            if len(s):
                return s[0].upper() + s[1:]
            else:
                return s

        elif id_ == Id.VOp1_DCaret:
            if arg != '':
                e_die("%s can't have an argument" % ui.PrettyId(id_), op_tok)
            return s.upper()

        else:  # e.g. ^ ^^ , ,,
            raise AssertionError(id_)

    # For patterns, do fnmatch() in a loop.
    #
    # TODO:
    # - Another potential fast path:
    #   v=aabbccdd
    #   echo ${v#*b}  # strip shortest prefix
    #
    # If the whole thing doesn't match '*b*', then no test can succeed.  So we
    # can fail early.  Conversely echo ${v%%c*} and '*c*'.
    #
    # (Although honestly this whole construct is nuts and should be deprecated.)

    n = len(s)

    if id_ == Id.VOp1_Pound:  # shortest prefix
        # 'abcd': match '', 'a', 'ab', 'abc', ...
        i = 0
        while True:
            assert i <= n
            #log('Matching pattern %r with %r', arg, s[:i])
            if libc.fnmatch(arg, s[:i]):
                return s[i:]
            if i >= n:
                break
            i = _NextUtf8Char(s, i)
        return s

    elif id_ == Id.VOp1_DPound:  # longest prefix
        # 'abcd': match 'abc', 'ab', 'a'
        i = n
        while True:
            assert i >= 0
            #log('Matching pattern %r with %r', arg, s[:i])
            if libc.fnmatch(arg, s[:i]):
                return s[i:]
            if i == 0:
                break
            i = PreviousUtf8Char(s, i)
        return s

    elif id_ == Id.VOp1_Percent:  # shortest suffix
        # 'abcd': match 'abcd', 'abc', 'ab', 'a'
        i = n
        while True:
            assert i >= 0
            #log('Matching pattern %r with %r', arg, s[:i])
            if libc.fnmatch(arg, s[i:]):
                return s[:i]
            if i == 0:
                break
            i = PreviousUtf8Char(s, i)
        return s

    elif id_ == Id.VOp1_DPercent:  # longest suffix
        # 'abcd': match 'abc', 'bc', 'c', ...
        i = 0
        while True:
            assert i <= n
            #log('Matching pattern %r with %r', arg, s[:i])
            if libc.fnmatch(arg, s[i:]):
                return s[:i]
            if i >= n:
                break
            i = _NextUtf8Char(s, i)
        return s

    else:
        raise NotImplementedError(ui.PrettyId(id_))


def _AllMatchPositions(s, regex):
    # type: (str, str) -> List[Tuple[int, int]]
    """Returns a list of all (start, end) match positions of the regex against
    s.

    (If there are no matches, it returns the empty list.)
    """
    matches = []  # type: List[Tuple[int, int]]
    pos = 0
    n = len(s)
    while pos < n:  # needed to prevent infinite loop in (.*) case
        m = libc.regex_first_group_match(regex, s, pos)
        if m is None:
            break
        matches.append(m)
        start, end = m
        pos = end  # advance position
    return matches


def _PatSubAll(s, regex, replace_str):
    # type: (str, str, str) -> str
    parts = []  # type: List[str]
    prev_end = 0
    for start, end in _AllMatchPositions(s, regex):
        parts.append(s[prev_end:start])
        parts.append(replace_str)
        prev_end = end
    parts.append(s[prev_end:])
    return ''.join(parts)


class GlobReplacer(object):
    def __init__(self, regex, replace_str, slash_tok):
        # type: (str, str, Token) -> None

        # TODO: It would be nice to cache the compilation of the regex here,
        # instead of just the string.  That would require more sophisticated use of
        # the Python/C API in libc.c, which we might want to avoid.
        self.regex = regex
        self.replace_str = replace_str
        self.slash_tok = slash_tok

    def __repr__(self):
        # type: () -> str
        return '<_GlobReplacer regex %r r %r>' % (self.regex, self.replace_str)

    def Replace(self, s, op):
        # type: (str, suffix_op.PatSub) -> str

        regex = '(%s)' % self.regex  # make it a group

        if op.replace_mode == Id.Lit_Slash:
            # Avoid infinite loop when replacing all copies of empty string
            if len(self.regex) == 0:
                return s

            try:
                return _PatSubAll(s, regex,
                                  self.replace_str)  # loop over matches
            except RuntimeError as e:
                # Not sure if this is possible since we convert from glob:
                # libc.regex_first_group_match raises RuntimeError on regex syntax
                # error.
                msg = e.message  # type: str
                e_die('Error matching regex %r: %s' % (regex, msg),
                      self.slash_tok)

        if op.replace_mode == Id.Lit_Pound:
            regex = '^' + regex
        elif op.replace_mode == Id.Lit_Percent:
            regex = regex + '$'

        m = libc.regex_first_group_match(regex, s, 0)
        #log('regex = %r, s = %r, match = %r', regex, s, m)
        if m is None:
            return s
        start, end = m
        return s[:start] + self.replace_str + s[end:]


def ShellQuoteB(s):
    # type: (str) -> str
    """Quote by adding backslashes.

    Used for autocompletion, so it's friendlier for display on the
    command line. We use the strategy above for other use cases.
    """
    # There's no way to escape a newline!  Bash prints ^J for some reason, but
    # we're more explicit.  This will happen if there's a newline on a file
    # system or a completion plugin returns a newline.

    # NOTE: tabs CAN be escaped with \.
    s = s.replace('\r', '<INVALID CR>').replace('\n', '<INVALID NEWLINE>')

    # ~ for home dir
    # ! for history
    # * [] ? for glob
    # {} for brace expansion
    # space because it separates words
    return pyutil.BackslashEscape(s, ' `~!$&*()[]{}\\|;\'"<>?')
