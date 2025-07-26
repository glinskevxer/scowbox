"""The work the office actually does with the book.

Everything under here reads records out, hands them to the rule modules and
hands the answer back. It is the only layer that knows both what is in the book
and what the rules want, and it holds no rules of its own: if a decision is
being made here rather than passed through, it is in the wrong place.
"""
