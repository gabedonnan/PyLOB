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
        self.orders.append(Node(order.id))
        self.quantity = order.quantity

    def __str__(self):
        return f"LimitLevel(price={self.price}, {self.orders.head.__str__()})"

    def append(self, order: Order):
        self.orders.append(Node(order.id))

    def pop_left(self) -> int:
        return self.orders.pop_left().value


class LimitOrderBook:
    def __init__(self):
        # Contain LimitLevel objects keyed by price, which are doubly linked lists holding nodes, quantities and prices
        # Each node contains an order ID, not the order itself
        self.bids = SortedDict()
        self.asks = SortedDict()

        # Stores the actual orders, keyed by order id
        self.orders = {}

        # ID for the next order to be generated
        self.order_id = 0

    def _pop_limit(self, limit_level: LimitLevel) -> int:
        """
        Utility function for the removal of the leftmost node from a limit tree
        Manages increases and reductions to quantity
        :param limit_level: a LimitLevel object
        :return: integer of order id from popped object
        """
        res = limit_level.pop_left()
        limit_level.quantity -= self.orders[res].quantity
        return res

    def _append_limit(self, limit_level: LimitLevel, order: Order):
        """
        Utility function for the addition of rightmost node in a limit tree
        Manages increases and reductions to quantity
        :param limit_level: a LimitLevel object
        :param order: an Order object
        :return: None
        """
        limit_level.append(order)
        limit_level.quantity += order.quantity

    def _add_order(self, order: Order):
        if order.id in self.orders:
            raise LOBException(f"Order with existing ID {order.id} attempted to be added to LimitOrderBook")

        # Determine whether order is a bid or an ask
        order_tree = self.bids if order.is_bid else self.asks

        # Price level does not exist already
        if order.price not in order_tree:
            self.orders[order.id] = order
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
            self.orders[order.id] = order

            # Adds bids to bid tree and asks to ask tree
            self._append_limit(order_tree[order.id], order)

    def _update_order(self, order: Order):
        return self.update(order.id, order.price, order.quantity)

    def bid(self, quantity: int, price: int) -> int:
        order = Order(True, quantity, price, self.order_id)
        self._add_order(order)
        self.order_id += 1
        return order.id

    def ask(self, quantity: int, price: int) -> int:
        order = Order(False, quantity, price, self.order_id)
        self._add_order(order)
        self.order_id += 1
        return order.id

    def update(self, order_id: int, price: int, quantity: int) -> int | None:
        """
        Updates an order, retrieved by order id.
        :param order_id: Order to update
        :param price: Price to change order to, a change here will result in an order cancellation and re-adding
        :param quantity: Quantity to change order to
        :return: New order id if quantity > 0 else None. May be the same as previous ID.
        """
        if quantity == 0:
            self.cancel(order_id)
        elif order_id in self.orders:
            order_tree = self.bids if self.orders[order_id].is_bid else self.asks
            price_difference = self.orders[order_id].price - price
            # Manages price adjustment
            if price_difference != 0:
                # Adjusting price requires order be moved to a separate layer
                # This is most easily done by deleting one order and creating a new one in a different price layer
                order_adder = self.bid if self.orders[order_id].is_bid else self.ask
                self.cancel(order_id)
                new_id = order_adder(quantity, price)
            else:
                # Manages quantity adjustment
                quantity_difference = self.orders[order_id].quantity - quantity
                # If quantity is reduced, the order may maintain order
                if quantity_difference >= 0:
                    self.orders[order_id].quantity = quantity
                    order_tree[price].quantity -= quantity_difference
                    new_id = order_id
                else:
                    # Obeys price-time priority, an increase in quantity means order is moved to back of queue
                    order_adder = self.bid if self.orders[order_id].is_bid else self.ask
                    self.cancel(order_id)
                    new_id = order_adder(quantity, price)
            return new_id
        else:
            raise LOBException("Attempted to update order which does not exist / no longer exists")

    def cancel(self, order_id: int):
        if order_id in self.orders:
            order_tree = self.bids if self.orders[order_id].is_bid else self.asks
            price_level = order_tree[self.orders[order_id].price]
            price_level.quantity -= self.orders[order_id].quantity
            if price_level.quantity <= 0:
                # delete order id from order_tree
                del order_tree[price_level.price]
            del self.orders[order_id]

        else:
            raise LOBException("Attempted to cancel order which does not exist / no longer exists")

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
            # Gets the order object from the LimitLevel's stored id
            order_id = best_value.orders.head.value
            if order_id in self.orders:
                head_order = self.orders[best_value.orders.head.value]
            else:
                # Remove orders that have been cancelled
                best_value.pop_left()
                continue
            if order.quantity <= head_order.quantity:
                # Reduce quantity of the limit level and its head simultaneously
                head_order -= order.quantity
                best_value.quantity -= order.quantity
                order.quantity = 0
            else:
                order.quantity -= head_order.quantity
                head_order.quantity = 0

            if head_order.quantity == 0:
                # Remove empty order and remove its corresponding quantity
                del self.orders[self._pop_limit(best_value)]

            if best_value.quantity <= 0:
                # delete order id from order_tree
                order_tree = self.bids if order.is_bid else self.asks
                del order_tree[best_value.price]

        if order.quantity > 0:
            if order.id in self.orders:
                self._update_order(order)
            else:
                self._add_order(order)






