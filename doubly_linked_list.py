class Node:
    def __init__(self, value, prev: "Node" = None, next: "Node" = None):
        self.value = value
        self.prev = prev
        self.next = next

    def __str__(self):
        return f"Node({self.value}, next={self.next})"

    def __repr__(self):
        return f"Node({self.value}, next={self.next})"


class DoublyLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self.length = 0

    def append(self, node: Node):
        if self.tail is None:
            self.head = node
            self.tail = node
        else:
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
        self.length += 1

    def append_left(self, node: Node):
        if self.head is None:
            self.head = node
            self.tail = node
        else:
            self.head.prev = node
            node.next = self.head
            self.head = node
        self.length += 1

    def insert(self, node: Node, pos: int):
        if pos >= self.length:
            self.append(node)
        elif pos <= 0:
            self.append_left(node)
        else:
            locator = self.head
            for i in range(pos - 1):
                locator = locator.next

            node.next = locator.next
            locator.next.prev = node
            node.prev = locator
            locator.next = node
            self.length += 1

    def remove(self, pos: int):
        if pos >= self.length:
            self.pop()
        elif pos <= 0:
            self.pop_left()
        else:
            locator = self.head
            for i in range(pos - 1):
                locator = locator.next

            secondary = locator.next

            locator.next = secondary.next
            secondary.next.prev = locator
            self.length -= 1

    def pop(self) -> Node:
        if self.tail is not None:
            if self.length >= 2:
                tail = self.tail
                tail.prev.next = None
                self.tail = tail.prev
                tail.prev = None
            else:
                tail = self.tail
                self.head = None
                self.tail = None
            self.length -= 1
            return tail

    def pop_left(self) -> Node:
        if self.head is not None:
            if self.length >= 2:
                head = self.head
                head.next.prev = None
                self.head = head.next
                head.next = None
            else:
                head = self.head
                self.head = None
                self.tail = None
            self.length -= 1
            return head

    def __str__(self):
        return f"DoublyLinkedList({self.head.__str__()})"

    def __repr__(self):
        return f"DoublyLinkedList({self.head.__repr__()})"

    def __len__(self):
        return self.length
