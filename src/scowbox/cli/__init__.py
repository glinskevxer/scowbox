"""The command line.

The only layer allowed to print. Everything below returns records and numbers;
this turns them into lines on a terminal and exit statuses, and it is the one
place a domain error becomes a message a project engineer reads.
"""
