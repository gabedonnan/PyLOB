from doubly_linked_list import DoublyLinkedList, Node
from sortedcontainers import SortedDict


class Order:
    def __init__(
            self,
            is_bid: bool,
            quantity: int,
            price: int,
            order_id: int
    ):
        self.is_bid = is_bid
        self.quantity = quantity
        self.price = price
        self.order_id = order_id

    def __str__(self):
        return f"Order({'BID' if self.is_bid else 'ASK'}, " \
               f"quantity={self.quantity}, " \
               f"price={self.price}, " \
               f"id={self.order_id})"

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return self.order_id


class LimitLevel:
    def __init__(self, order: Order):
        self.price = order.price
        self.orders = DoublyLinkedList()
        self.orders.append(Node(order))
        self.quantity = order.quantity

    def append(self, order: Order):
        self.orders.append(Node(order))
        self.quantity += order.quantity

    def remove(self, order_id: int):
        ...


class LimitOrderBook:
    def __init__(self):
        self.bids = SortedDict()
        self.asks = SortedDict()
        self.price_levels = {}
        self.orders = {}
        self.order_id = 0

    def _add_order(self, order: Order):
        order_tree = self.bids if order.is_bid else self.asks
        if order.price not in self.price_levels:
            order_tree[order.price] = LimitLevel(order)
            self.price_levels[order.price] = order.quantity
        else:
            ...

    def bid(self, quantity: int, price: int):
        order = Order(True, quantity, price, self.order_id)
        self._add_order(order)
        self.order_id += 1

    def ask(self, quantity: int, price: int):
        order = Order(False, quantity, price, self.order_id)
        self._add_order(order)
        self.order_id += 1




