# PyLOB
An efficient implementation of a limit order book in Python
Created as a learning experience, any tips on improvement are always welcome.

Addition (bids / asks): O(log(n)) for the first addition at each price point, O(1) for every subsequent addition

Cancellation: O(1), with the stipulation that deleted records remain in rows until their quantity drops to zero or they are manually eliminated during matching

Matching: O(n), though this is practically normally n is very small

Updating: O(1)
