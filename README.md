# PyLOB
An efficient implementation of a limit order book in Python
Created as a learning experience, any tips on improvement are always welcome.

Addition (bids / asks): O(log(n)) for the first addition at each price point, O(1) for every subsequent addition

Cancellation: O(1), 
with the stipulation that deleted records remain in price rows until either:
- their quantity drops to zero 
- they are manually eliminated during matching

This is done to ensure that deletion is extremely fast as it is very common and the rarer match operations will take the performance burden.

Matching: O(n), though often n is very small

Updating: O(1)
