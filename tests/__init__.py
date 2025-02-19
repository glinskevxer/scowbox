"""The test suite is a package.

Two suites here would otherwise both be called ``test_volume``: the one over
cubic yards and the one over average end area. Without these files mypy sees a
duplicate module and stops before it has checked anything. Naming them
``test_unit_volume`` and ``test_section_volume`` instead would make every file
in the tree carry the name of its directory a second time.
"""
