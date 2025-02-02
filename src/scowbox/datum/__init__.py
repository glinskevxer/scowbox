"""Getting a reading onto the datum the contract is written against.

A transducer reads the distance from itself to the bed. The contract is written
in feet below mean lower low water. Between those two numbers sit the tide at
the moment of the reading, the draft of the transducer, the squat of the vessel
at survey speed, and the index correction from the bar check. This package
holds all four and nothing else.
"""
