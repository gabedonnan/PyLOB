from doubly_linked_list import DoublyLinkedList, Node
from sortedcontainers import SortedDict


class LOBException(Exception):
    """
    Raised when an exception occurs within a limit order book
    """
    ...


class Order:
    def __init__(
            self,
            is_bid: bool,
            quantity: int,
            price: int,
            id: int
    ):
        self.is_bid = is_bid
        self.quantity = quantity
        self.price = price
        self.id = id

    def __str__(self):
        return f"Order({'BID' if self.is_bid else 'ASK'}, " \
               f"quantity={self.quantity}, " \
               f"price={self.price}, " \
               f"id={self.id})"

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return self.id


class LimitLevel:
    def __init__(self, order: Order):
        self.price = order.price
        self.orders = DoublyLinkedList()
        self.orders.append(Node(order))
        self.quantity = order.quantity

    def __str__(self):
        return f"LimitLevel(price={self.price}, {self.orders.head.__str__()})"

    def append(self, order: Order):
        self.orders.append(Node(order))
        self.quantity += order.quantity


class LimitOrderBook:
    def __init__(self):
        self.bids = SortedDict()
        self.asks = SortedDict()
        self.orders = set()
        self.order_id = 0

    def _add_order(self, order: Order):
        if order.id in self.orders:
            raise LOBException(f"Order with existing ID {order.id} attempted to be added to LimitOrderBook")

        # Determine whether order is a bid or an ask
        order_tree = self.bids if order.is_bid else self.asks

        # Price level does not exist already
        if order.price not in order_tree:
            self.orders.add(order.id)
            order_tree[order.price] = LimitLevel(order)
        else:
            # Check if bid crosses spread to match an ask
            if order.is_bid and (best_ask := self.get_best_ask()) is not None:
                if best_ask.price <= order.price:
                    self.match_orders(order, best_ask)
                    return
            # Check if ask crosses spread to match a bid
            elif not order.is_bid and (best_bid := self.get_best_bid()) is not None:
                if best_bid.price >= order.price:
                    self.match_orders(order, best_bid)
                    return

            # Adds order id to order tracker
            self.orders.add(order.id)

            # Adds bids to bid tree and asks to ask tree
            order_tree[order.id].append(order)

    def bid(self, quantity: int, price: int):
        order = Order(True, quantity, price, self.order_id)
        self._add_order(order)
        self.order_id += 1

    def ask(self, quantity: int, price: int):
        order = Order(False, quantity, price, self.order_id)
        self._add_order(order)
        self.order_id += 1

    def get_best_bid(self):
        try:
            return self.bids.peekitem()
        except IndexError:
            return None

    def get_best_ask(self):
        try:
            return self.asks.peekitem(0)
        except IndexError:
            return None

    def match_orders(self, order: Order, best_value: LimitLevel):
        while best_value.quantity > 0 and order.quantity > 0:
            head_order = best_value.orders.head
            if order.quantity <= head_order.quantity:
                order.quantity = 0
                head_order -= order.quantity
            else:
                ...





