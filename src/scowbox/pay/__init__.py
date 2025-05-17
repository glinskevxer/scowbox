"""Turning quantities into money.

A progress estimate is a cumulative document. Every line carries the quantity to
date, not the quantity this month, and what is paid this month is the difference
between what is now due and what has already been paid. Building it the other
way round, month by month, means a correction to March has to be carried
forward by hand into every month after it.
"""
