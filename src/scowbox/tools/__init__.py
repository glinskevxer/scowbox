"""Checks the build runs on itself.

These are not tests. A test says a function does what it is meant to do; a
check here says something about the shape of the whole package that no single
test is in a position to see. Every one of them exits non zero with a list of
what it found, so CI can run them the same way it runs anything else.

Every check has a test that feeds it something broken and asserts it fires. A
check that has only ever passed has not been seen to work.
"""
