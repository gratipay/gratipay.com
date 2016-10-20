from gratipay import inventory
from gratipay.testing import Harness


class Tests(Harness):

    def test_inventory_python_returns_something(self):
        inventory.python('Django')
