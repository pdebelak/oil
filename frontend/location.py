#!/usr/bin/env python2
"""
location.py - Library to get source location info from nodes.

This makes syntax errors nicer.
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import (
    loc,
    loc_t,
    loc_e,
    command,
    command_e,
    command_t,
    sh_lhs_expr,
    sh_lhs_expr_e,
    sh_lhs_expr_t,
    word,
    word_e,
    word_t,
    word_part,
    word_part_e,
    word_part_t,
    CompoundWord,
    SimpleVarSub,
    Token,
    ShArrayLiteral,
    SingleQuoted,
    DoubleQuoted,
    CommandSub,
    BracedVarSub,
    BraceGroup,
    arith_expr_e,
    arith_expr_t,
)
from _devbuild.gen.runtime_asdl import lvalue
from mycpp.mylib import log
from mycpp.mylib import tagswitch

_ = log

from typing import cast, Optional


def LName(name):
    # type: (str) -> lvalue.Named
    """Wrapper for lvalue.Named() with location.

    TODO: add locations and remove
    this.
    """
    return lvalue.Named(name, loc.Missing)


def TokenFor(loc_):
    # type: (loc_t) -> Optional[Token]
    """Given a location, get a Token.

    This is useful because a Token points to a single line.
    """
    UP_location = loc_
    with tagswitch(loc_) as case:
        if case(loc_e.Missing):
            return None

        elif case(loc_e.Token):
            tok = cast(Token, UP_location)
            if tok:
                return tok
            else:
                return None

        elif case(loc_e.ArgWord):
            w = cast(CompoundWord, UP_location)
            return LeftTokenForWord(w)

        elif case(loc_e.WordPart):
            loc_ = cast(loc.WordPart, UP_location)
            if loc_.p:
                return LeftTokenForWordPart(loc_.p)
            else:
                return None

        elif case(loc_e.Word):
            loc_ = cast(loc.Word, UP_location)
            if loc_.w:
                return LeftTokenForWord(loc_.w)
            else:
                return None

        elif case(loc_e.Command):
            loc_ = cast(loc.Command, UP_location)
            if loc_.c:
                return TokenForCommand(loc_.c)
            else:
                return None

        elif case(loc_e.Arith):
            loc_ = cast(loc.Arith, UP_location)
            if loc_.a:
                return TokenForArith(loc_.a)
            else:
                return None

        else:
            raise AssertionError()

    raise AssertionError()


def TokenForCommand(node):
    # type: (command_t) -> Optional[Token]
    """Used directly in _CheckStatus()"""
    UP_node = node  # type: command_t
    tag = node.tag()

    if tag == command_e.Sentence:
        node = cast(command.Sentence, UP_node)
        #log("node.child %s", node.child)
        return node.terminator  # & or ;

    if tag == command_e.Simple:
        node = cast(command.Simple, UP_node)
        return node.blame_tok

    if tag == command_e.ShAssignment:
        node = cast(command.ShAssignment, UP_node)
        return node.left

    if tag == command_e.Pipeline:
        node = cast(command.Pipeline, UP_node)
        if len(node.ops):
            return node.ops[0]  # first | or |&
        else:
            assert node.negated is not None
            return node.negated  # ! false

    if tag == command_e.AndOr:
        node = cast(command.AndOr, UP_node)
        return node.ops[0]  # first && or ||

    if tag == command_e.DoGroup:
        node = cast(command.DoGroup, UP_node)
        return node.left  # 'do' token
    if tag == command_e.BraceGroup:
        node = cast(BraceGroup, UP_node)
        return node.left  # { token
    if tag == command_e.Subshell:
        node = cast(command.Subshell, UP_node)
        return node.left  # ( token

    if tag == command_e.WhileUntil:
        node = cast(command.WhileUntil, UP_node)
        return node.keyword  # while
    if tag == command_e.If:
        node = cast(command.If, UP_node)
        return node.if_kw
    if tag == command_e.Case:
        node = cast(command.Case, UP_node)
        return node.case_kw
    if tag == command_e.TimeBlock:
        node = cast(command.TimeBlock, UP_node)
        return node.keyword

    # We never have this case?
    #if node.tag == command_e.CommandList:
    #  pass

    return None


def TokenForArith(node):
    # type: (arith_expr_t) -> Optional[Token]
    UP_node = node
    with tagswitch(node) as case:
        if case(arith_expr_e.VarSub):
            vsub = cast(SimpleVarSub, UP_node)
            return vsub.left
        elif case(arith_expr_e.Word):
            w = cast(CompoundWord, UP_node)
            return LeftTokenForWord(w)

        # TODO: Fill in other cases

    return None


def LeftTokenForWordPart(part):
    # type: (word_part_t) -> Optional[Token]
    UP_part = part
    with tagswitch(part) as case:
        if case(word_part_e.ShArrayLiteral):
            part = cast(ShArrayLiteral, UP_part)
            return part.left

        elif case(word_part_e.AssocArrayLiteral):
            part = cast(word_part.AssocArrayLiteral, UP_part)
            return part.left

        elif case(word_part_e.Literal):
            tok = cast(Token, UP_part)
            return tok

        elif case(word_part_e.EscapedLiteral):
            part = cast(word_part.EscapedLiteral, UP_part)
            return part.token

        elif case(word_part_e.SingleQuoted):
            part = cast(SingleQuoted, UP_part)
            return part.left

        elif case(word_part_e.DoubleQuoted):
            part = cast(DoubleQuoted, UP_part)
            return part.left

        elif case(word_part_e.SimpleVarSub):
            part = cast(SimpleVarSub, UP_part)
            return part.left

        elif case(word_part_e.BracedVarSub):
            part = cast(BracedVarSub, UP_part)
            return part.left

        elif case(word_part_e.CommandSub):
            part = cast(CommandSub, UP_part)
            return part.left_token

        elif case(word_part_e.TildeSub):
            part = cast(word_part.TildeSub, UP_part)
            return part.token

        elif case(word_part_e.ArithSub):
            part = cast(word_part.ArithSub, UP_part)
            return part.left

        elif case(word_part_e.ExtGlob):
            part = cast(word_part.ExtGlob, UP_part)
            return part.op

        elif case(word_part_e.BracedRange):
            part = cast(word_part.BracedRange, UP_part)
            return part.blame_tok

        elif case(word_part_e.BracedTuple):
            part = cast(word_part.BracedTuple, UP_part)
            # TODO: Derive token from part.words[0]
            return None

        elif case(word_part_e.Splice):
            part = cast(word_part.Splice, UP_part)
            return part.blame_tok

        elif case(word_part_e.ExprSub):
            part = cast(word_part.ExprSub, UP_part)
            return part.left  # $[

        else:
            raise AssertionError(part.tag())


def _RightTokenForWordPart(part):
    # type: (word_part_t) -> Token
    UP_part = part
    with tagswitch(part) as case:
        if case(word_part_e.ShArrayLiteral):
            part = cast(ShArrayLiteral, UP_part)
            return part.right

        elif case(word_part_e.AssocArrayLiteral):
            part = cast(word_part.AssocArrayLiteral, UP_part)
            return part.right

        elif case(word_part_e.Literal):
            tok = cast(Token, UP_part)
            # Just use the token
            return tok

        elif case(word_part_e.EscapedLiteral):
            part = cast(word_part.EscapedLiteral, UP_part)
            return part.token

        elif case(word_part_e.SingleQuoted):
            part = cast(SingleQuoted, UP_part)
            return part.right  # right '

        elif case(word_part_e.DoubleQuoted):
            part = cast(DoubleQuoted, UP_part)
            return part.right  # right "

        elif case(word_part_e.SimpleVarSub):
            part = cast(SimpleVarSub, UP_part)
            # left and right are the same for $myvar
            return part.left

        elif case(word_part_e.BracedVarSub):
            part = cast(BracedVarSub, UP_part)
            return part.right

        elif case(word_part_e.CommandSub):
            part = cast(CommandSub, UP_part)
            return part.right

        elif case(word_part_e.TildeSub):
            part = cast(word_part.TildeSub, UP_part)
            return part.token

        elif case(word_part_e.ArithSub):
            part = cast(word_part.ArithSub, UP_part)
            return part.right

        elif case(word_part_e.ExtGlob):
            part = cast(word_part.ExtGlob, UP_part)
            return part.right

        elif case(word_part_e.BracedRange):
            part = cast(word_part.BracedRange, UP_part)
            return part.blame_tok

        elif case(word_part_e.BracedTuple):
            part = cast(word_part.BracedTuple, UP_part)
            # TODO: Derive token from part.words[0]
            return None

        elif case(word_part_e.Splice):
            part = cast(word_part.Splice, UP_part)
            return part.blame_tok

        elif case(word_part_e.ExprSub):
            part = cast(word_part.ExprSub, UP_part)
            return part.right

        else:
            raise AssertionError(part.tag())


def LeftTokenForCompoundWord(w):
    # type: (CompoundWord) -> Optional[Token]
    if len(w.parts):
        return LeftTokenForWordPart(w.parts[0])
    else:
        # This is possible for empty brace sub alternative {a,b,}
        return None


def LeftTokenForWord(w):
    # type: (word_t) -> Optional[Token]
    if w is None:
        return None  # e.g. builtin_bracket word.String() EOF

    UP_w = w
    with tagswitch(w) as case:
        if case(word_e.Compound):
            w = cast(CompoundWord, UP_w)
            return LeftTokenForCompoundWord(w)

        elif case(word_e.Token):
            tok = cast(Token, UP_w)
            return tok

        elif case(word_e.BracedTree):
            w = cast(word.BracedTree, UP_w)
            # This should always have one part?
            return LeftTokenForWordPart(w.parts[0])

        elif case(word_e.String):
            w = cast(word.String, UP_w)
            # See _StringWordEmitter in osh/builtin_bracket.py
            return LeftTokenForWord(w.blame_loc)

        else:
            raise AssertionError(w.tag())

    raise AssertionError('for -Wreturn-type in C++')


def RightTokenForWord(w):
    # type: (word_t) -> Token
    """Used for alias expansion and history substitution.

    and here doc delimiters?
    """
    UP_w = w
    with tagswitch(w) as case:
        if case(word_e.Compound):
            w = cast(CompoundWord, UP_w)
            if len(w.parts):
                end = w.parts[-1]
                return _RightTokenForWordPart(end)
            else:
                # This is possible for empty brace sub alternative {a,b,}
                return None

        elif case(word_e.Token):
            tok = cast(Token, UP_w)
            return tok

        elif case(word_e.BracedTree):
            w = cast(word.BracedTree, UP_w)
            # Note: this case may be unused
            return _RightTokenForWordPart(w.parts[-1])

        elif case(word_e.String):
            w = cast(word.String, UP_w)
            # Note: this case may be unused
            return RightTokenForWord(w.blame_loc)

        else:
            raise AssertionError(w.tag())

    raise AssertionError('for -Wreturn-type in C++')


def TokenForLhsExpr(node):
    # type: (sh_lhs_expr_t) -> Token
    """Currently unused?

    Will be useful for translating YSH assignment
    """
    # This switch is annoying but we don't have inheritance from the sum type
    # (because of diamond issue).  We might change the schema later, which maeks
    # it moot.  See the comment in frontend/syntax.asdl.
    UP_node = node
    with tagswitch(node) as case:
        if case(sh_lhs_expr_e.Name):
            node = cast(sh_lhs_expr.Name, UP_node)
            return node.left
        elif case(sh_lhs_expr_e.IndexedName):
            node = cast(sh_lhs_expr.IndexedName, UP_node)
            return node.left
        else:
            # Should not see UnparsedIndex
            raise AssertionError()

    raise AssertionError()
