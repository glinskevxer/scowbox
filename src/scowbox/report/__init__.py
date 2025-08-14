"""Reports.

Every renderer here returns a list of lines and prints nothing. That is what
makes them testable: a report is a value, and a test can assert on the line it
cares about instead of capturing a stream and hoping.
"""
