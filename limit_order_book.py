import threading

from collections import deque
from sortedcontainers import SortedDict


class LOBException(Exception):
    """
    Raised when an exception occurs within a limit order book
    """
    ...


class Order:
    def __init__(self, is_bid: bool, quantity: int, price: int, id: int):
        self.is_bid = is_bid
        self.quantity = quantity
        self.price = price
        self.id = id

    def __str__(self):
        return (
            f"Order({'BID' if self.is_bid else 'ASK'}, "
            f"quantity={self.quantity}, "
            f"price={self.price}, "
            f"id={self.id})"
        )

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return self.id


class LimitLevel:
    def __init__(self, order: Order):
        self.price = order.price
        self.orders = deque([order.id])
        self.quantity = order.quantity

    def __str__(self):
        return f"LimitLevel(price={self.price}, quantity={self.quantity}, order_ids={self.orders})"

    def __repr__(self):
        return self.__str__()

    def append(self, order: Order):
        self.orders.append(order.id)

    def pop_left(self) -> int:
        return self.orders.popleft()


class LimitOrderBook:
    def __init__(self, title: str = "", currency_symbol: str = ""):
        # Contain LimitLevel objects keyed by price, which are doubly linked lists holding nodes, quantities and prices
        # Each node contains an order ID, not the order itself
        self.bids = SortedDict()
        self.asks = SortedDict()

        # Stores the actual orders, keyed by order id
        self.orders = {}

        # ID for the next order to be generated
        self.order_id = 0

        # Threading lock to ensure thread safety
        self.lock = threading.Lock()

        # LOB title
        self.title = title

        # Currency symbol for string representation
        self.currency_symbol = currency_symbol

    def __str__(self):
        final_str_list = [f"LimitOrderBook {self.title}", "BIDS:"]
        for price, level in self.bids.items():
            final_str_list.append(f"    {level.quantity} @ {self.currency_symbol}{price}")

        final_str_list.append("ASKS:")
        for price, level in self.asks.items():
            final_str_list.append(f"    {level.quantity} @ {self.currency_symbol}{price}")
        return "\n".join(final_str_list)

    def __repr__(self):
        return self.__str__()

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

    @staticmethod
    def _append_limit(limit_level: LimitLevel, order: Order):
        """
        Utility function for the addition of rightmost node in a limit tree
        Manages increases and reductions to quantity
        :param limit_level: a LimitLevel object
        :param order: an Order object
        :return: None
        """
        limit_level.append(order)
        limit_level.quantity += order.quantity

    def _add_order(self, order: Order, acquire_locks: bool = True):
        if order.id in self.orders:
            raise LOBException(
                f"Order with existing ID {order.id} attempted to be added to LimitOrderBook"
            )

        # Determine whether order is a bid or an ask
        order_tree = self.bids if order.is_bid else self.asks

        # Price level does not exist already
        if order.is_bid and (best_ask := self.get_best_ask()) is not None:
            if best_ask.price <= order.price:
                if acquire_locks:
                    self.lock.acquire()
                self._match_orders(order, best_ask)
                if acquire_locks:
                    self.lock.release()
                return

        # Check if ask crosses spread to match a bid
        elif not order.is_bid and (best_bid := self.get_best_bid()) is not None:
            if best_bid.price >= order.price:
                if acquire_locks:
                    self.lock.acquire()
                self._match_orders(order, best_bid)
                if acquire_locks:
                    self.lock.release()
                return

        if order.quantity > 0:
            self.orders[order.id] = order
            if order.price not in order_tree:
                order_tree[order.price] = LimitLevel(order)
            else:
                self._append_limit(order_tree[order.price], order)

    def _match_orders(self, order: Order, best_value: LimitLevel):
        if best_value is None:
            return

        while (
            best_value.quantity > 0
            and order.quantity > 0
            and best_value.orders[0] is not None
        ):
            # Gets the order object from the LimitLevel's stored id
            order_id = best_value.orders[0]
            if order_id in self.orders:
                head_order = self.orders[best_value.orders[0]]
            else:
                # Remove orders that have been cancelled
                best_value.pop_left()
                continue

            if order.quantity <= head_order.quantity:
                # Reduce quantity of the limit level and its head simultaneously
                head_order.quantity -= order.quantity
                best_value.quantity -= order.quantity
                order.quantity = 0
            else:
                # Deplete the head order quantity and subtract matching order quantity
                best_value.quantity -= order.quantity
                order.quantity -= head_order.quantity
                head_order.quantity = 0

            if order.quantity == 0 and order.id in self.orders:
                self.cancel(order.id)

            if head_order.quantity == 0 and head_order.id in self.orders:
                # Remove empty order and remove its corresponding quantity
                del self.orders[self._pop_limit(best_value)]

        if best_value.quantity <= 0 and best_value.price in (
            order_tree := self.asks if order.is_bid else self.bids
        ):
            # delete order id from order_tree
            del order_tree[best_value.price]

        if order.quantity > 0:
            if order.id in self.orders:
                self._update_order(order)
            else:
                self._add_order(order, False)

    def _update_order(self, order: Order):
        return self.update(order.id, order.price, order.quantity)

    def read_file(
        self, fname: str, line_format: str = "{Type},{ID},{Price},{Quantity}"
    ) -> set[int]:
        """
        :param fname: file name
        :param line_format: Format of file lines to read

        line_format structured like: "{Type},{ID},{Price},{Quantity}", with Type, ID, Price and Quantity in any order.
        {ID} is disregarded as the LOB does ID assignment by itself

        Any fields that are not any of these can be marked with a {*}, {}, or simply left as a space between commas
        """

        # Dictionary mapping locations to Type, Price and Quantity
        # ID is not mapped as it is overwritten
        split_format = {
            item: i
            for i, item in enumerate(line_format.split(","))
            if item
            in {
                "{Type}",
                "{Price}",
                "{Quantity}",
            }
        }
        ids = set()

        with open(fname, "r") as file:
            for line in file.readlines():
                split_line = line.split(",")

                tx_type = split_line[split_format["{Type}"]]
                price = int(split_line[split_format["{Price}"]])
                quantity = int(split_line[split_format["{Quantity}"]])

                if tx_type.lower() in {"b", "bid", "buy"}:
                    ids.add(self.bid(quantity=quantity, price=price))
                else:
                    ids.add(self.ask(quantity=quantity, price=price))

        return ids

    def bid(self, quantity: int, price: int) -> int:
        self.lock.acquire()
        order = Order(True, quantity, price, self.order_id)
        self.order_id += 1
        self.lock.release()
        self._add_order(order)
        return order.id

    def ask(self, quantity: int, price: int) -> int:
        self.lock.acquire()
        order = Order(False, quantity, price, self.order_id)
        self.order_id += 1
        self.lock.release()
        self._add_order(order)
        return order.id

    def update(self, order_id: int, quantity: int, price: int) -> int | None:
        """
        Updates an order, retrieved by order id.
        :param order_id: Order to update
        :param price: Price to change order to, a change here will result in an order cancellation and re-adding
        :param quantity: Quantity to change order to
        :return: New order id if quantity > 0 else None. The result may be the same as previous ID.
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
                # If quantity is reduced, the order of bids / asks are maintained
                if quantity_difference >= 0:
                    self.orders[order_id].quantity = quantity
                    if price in order_tree:
                        order_tree[price].quantity -= quantity_difference
                    new_id = order_id
                else:
                    # Obeys price-time priority, an increase in quantity means order is moved to back of queue
                    order_adder = self.bid if self.orders[order_id].is_bid else self.ask
                    self.cancel(order_id)
                    new_id = order_adder(quantity, price)
            return new_id
        else:
            raise LOBException(
                "Attempted to update order which does not exist / no longer exists"
            )

    def cancel(self, order_id: int):
        if order_id in self.orders:
            order_tree = self.bids if self.orders[order_id].is_bid else self.asks
            price_level = order_tree[self.orders[order_id].price]
            # Remove quantity of removed order
            price_level.quantity -= self.orders[order_id].quantity
            if price_level.quantity <= 0:
                # delete order id from order_tree
                del order_tree[price_level.price]
            del self.orders[order_id]

    def get_best_bid(self):
        try:
            return self.bids.peekitem()[1]
        except IndexError:
            return None

    def get_best_ask(self):
        try:
            return self.asks.peekitem(0)[1]
        except IndexError:
            return None
