MARCH - Multi Arch Wrapper Script
=================================

Utility program for the execution of machine-optimised alternatives.
The general system setting is done via kernel command line: march={v2,v3,v4}
If the parent directory of some program exists with a -march suffix and contains
an executable with the same name, run that instead of program.
 
Example
-------
Existing layout
```
/usr/bin/prog       # standard program
/usr/bin-v3/prog    # optimised version of program

# executing prog via march

march -mv3 prog

# result in execution of /usr/bin-v3/prog
```

Notes
-----
The same holds true, if you insert `/usr/bin-v3` before `/usr/bin` in `$PATH`
of course, but `march` does not require any `$PATH` modification and will work 
with executables in non-standard paths as well.

