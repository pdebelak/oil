---
default_highlighter: oil-sh
---

YSH FAQ
=======

Here are some common questions about [YSH]($xref).  Many of the answers boil
down to the fact that Oil is a **smooth upgrade** from [bash]($xref).

Old and new constructs exist side-by-side.  New constructs have fewer
"gotchas".

<!-- cmark.py expands this -->
<div id="toc">
</div>

## What's the difference `myvar`, `$myvar`, and `"$myvar"` ?

Oil is more like Python/JavaScript rather than PHP/Perl, so it doesn't use the
`$` sigil as much.

Never use `$` on the left-hand side:

    var mystr = "foo"   # not var $mystr

Use `$` to **substitute** vars into commands:

    echo $mystr
    echo $mystr/subdir  # no quotes in commands

or quoted strings:

    echo "$mystr/subdir"
    var x = "$mystr/subdir"

Rarely use `$` on the right-hand side:

    var x = mystr       # preferred
    var x = $mystr      # ILLEGAL -- use remove $
    var x = ${mystr:-}  # occasionally useful

    var x = $?          # allowed

See [Command vs. Expression Mode](command-vs-expression-mode.html) for more
details.

## How do I write `~/src` or `~bob/git` in a YSH assignment?

This should cover 80% of cases:

    var path = "$HOME/src"  # equivalent to ~/src

The old shell style will cover the remaining cases:

    declare path=~/src
    readonly other=~bob/git

---

This is only in issue in *expressions*.  The traditional shell idioms work in
*command* mode:

    echo ~/src ~bob/git
    # => /home/alice/src /home/bob/git

The underlying design issue is that the YSH expression `~bob` looks like a
unary operator and a variable, not some kind of string substitution.

Also, quoted `"~"` is a literal tilde, and shells disagree on what `~""` means.
The rules are subtle, so we avoid inventing new ones.

## How do I write `echo -e` or `echo -n`?

To escape variables, you can use the string language, rather than `echo`:

    echo $'tab \t newline \n'   # YES
    echo j"tab \t newline \n"   # TODO: J8 notation

    echo -e tab \t newline \n'  # NO

To omit the newline, use the `write` builtin:

    write -n 'prefix'           # YES
    write --end '' -- 'prefix'  # synonym

    echo -n 'prefix'            # NO

### Why Were `-e` and `-n` Removed?

Without the flags, you can write `echo $flag` without the 2 corner cases that
are impossible to fix.  Shell's `echo` doesn't accept `--`.

Note that `write -- $x` is equivalent to `echo $x` in YSH, so `echo` is
superfluous.  But we wanted the short and familiar `echo $x` to work.

## What's the difference between `$(dirname $x)` and `$[len(x)]` ?

Superficially, both of these syntaxes take an argument `x` and return a
string.  But they are different:

- `$(dirname $x)` is a shell command substitution that returns a string, and
  **starts another process**.
- `$[len(x)]` is an expression sub containing a function call expression.
  - It doesn't need to start a process.
  - Note that `len(x)` evaluates to an integer, and `$[len(x)]` converts it to
    a string.

<!--
(Note: builtin subs like `${.myproc $x}` are meant to eliminate process
overhead, but they're not yet implemented.)
-->

## How can I return rich values from shell functions / Oil `proc`s?

There are two primary ways:

- Print the "returned" data to `stdout`.  Retrieve it with a command sub like
  `$(myproc)` or a pipeline like `myproc | read --line`.
- Use an "out param" with [setref]($oil-help:setref).

(Oil may grow true functions with the `func` keyword, but it will be built on
top of `proc` and the *builtin sub* mechanism.)

Send us feedback if this doesn't make sense, or if you want a longer
explanation.

## Why doesn't a raw string work here: `${array[r'\']}` ?

This boils down to the difference between OSH and Oil, and not being able to
mix the two.  Though they look similar, `${array[i]}` syntax (with braces) is
fundamentally different than `$[array[i]]` syntax (with brackets).

- OSH supports `${array[i]}`.
  - The index is legacy/deprecated shell arithmetic like `${array[i++]}` or
    `${assoc["$key"]}`.
  - The index **cannot** be a raw string like `r'\'`.
- Oil supports both, but [expression substitution]($oil-help:expr-sub) syntax
  `$[array[i]]` is preferred.
  - It accepts Oil expressions like `$[array[i + 1]` or `$[mydict[key]]`.
  - A raw string like `r'\'` is a valid key, e.g.  `$[mydict[r'\']]`.

Of course, Oil style is preferred when compatibility isn't an issue.

No:

    echo ${array[r'\']}

Yes:

    echo $[array[r'\']]

A similar issue exists with arithmetic.

Old:

    echo $((1 + 2))   # shell arithmetic

New:

    echo $[1 + 2]     # Oil expression

<!--

## Why doesn't the ternary operator work here: `${array[0 if cond else 5]}`?

The issue is the same as above.  Oil expression are allowed within `$[]` but
not `${}`.

-->

## Related

- [Oil Language FAQ]($wiki) on the wiki has more answers.  They may be migrated
  here at some point.

