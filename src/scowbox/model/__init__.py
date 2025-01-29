"""Records, as they are written down.

Frozen dataclasses with validation in ``__post_init__`` and nothing else. No
database, no arithmetic that belongs to a rule, no formatting. A record that
exists is a record whose fields are individually possible; whether it is
allowed is a question for the rule modules above.
"""
