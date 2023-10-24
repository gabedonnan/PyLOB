from limit_order_book import LimitOrderBook


def test_file(fname: str):
    x = LimitOrderBook()
    x.read_file(fname)
    print(x)


if __name__ == "__main__":
    test_file("./LOBTests/MinimalTest.txt")
    test_file("./LOBTests/MinimalTest2.txt")
