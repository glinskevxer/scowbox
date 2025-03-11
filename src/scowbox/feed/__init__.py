"""Reading the files other people's software writes.

Sounding exports and gauge downloads arrive as comma separated text. This
package turns them into records and refuses the rest. Every error names the
line it came from, because a survey export is forty thousand lines long and
"could not parse a depth" without a line number is not a message anybody can
act on.
"""
