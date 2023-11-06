import random
import threading
from time import time

from limit_order_book import LimitOrderBook, Trader


def test_file(fname: str):
    x = LimitOrderBook()
    x.read_file(fname)
    print(x)


def stress_test_adding():
    x = LimitOrderBook()
    t0 = time()
    for i in range(1_000_000):
        x.bid(10, 10)
    print(time() - t0)


def stress_test_updating():
    x = LimitOrderBook()
    cur_id = x.bid(10, 10)
    t0 = time()
    for i in range(1_000_000):
        cur_id = x.update(cur_id, 10, 10)
    print(time() - t0)


def stress_test_add_cancel():
    x = LimitOrderBook()
    t0 = time()
    for i in range(1_000_000):
        cur_id = x.bid(10, 10)
        x.cancel(cur_id)
    print(time() - t0)


def stress_test_add_matching():
    x = LimitOrderBook(record_match_history=False)
    t0 = time()
    for i in range(1_000_000):
        x.bid(10, 10)

    for i in range(1_000_000):
        x.ask(10, 10)
    print(time() - t0)


def threading_helper_add_cancel(lob: LimitOrderBook):
    for i in range(10_000):
        lob.bid(10, random.randint(10, 100))

    for i in range(10_000):
        lob.ask(10, random.randint(10, 100))


def stress_test_multithread_matching():
    x = LimitOrderBook()
    t0 = time()
    for i in range(10):
        t = threading.Thread(target=threading_helper_add_cancel, args=(x,))
        t.start()

    cur_thread = threading.current_thread()
    for t in threading.enumerate():
        if t is not cur_thread:
            t.join()

    print(x)
    print(time() - t0)


def trader_tests():
    x = LimitOrderBook(asset_name="APL")
    t0 = time()
    trader_one = Trader()
    for i in range(10):
        x.ask(10, 8, trader_one)
        print(trader_one)

    trader_two = Trader()
    for i in range(10):
        x.bid(5, 10, trader_two)
        print(trader_one, trader_two)

    for i in range(10):
        x.ask(5, 7, trader_two)

    for i in range(10):
        x.bid(5, 7, trader_one)
        print(trader_one, trader_two)


if __name__ == "__main__":
    # test_file("./LOBTests/MinimalTest.txt")
    # test_file("./LOBTests/MinimalTest2.txt")
    # stress_test_updating()
    # stress_test_add_cancel()
    # stress_test_add_matching()
    # stress_test_multithread_matching()
    trader_tests()
