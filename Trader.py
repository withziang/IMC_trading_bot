from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string
import jsonpickle


class Trader:
    def run(self, state: TradingState):
        try:
            # Only method required. It takes all buy and sell orders for all symbols as an input, and outputs a list of orders to be sent
            print("traderData: " + state.traderData)
            print("Observations: " + str(state.observations))
            result = {}

            # get previous state
            if not state.traderData:
                previous_data = "x"
            else:
                previous_data = "x"

            for product in state.order_depths:
                order_depth: OrderDepth = state.order_depths[product]
                orders: List[Order] = []


                # check current portfolio




                # check if it is a good entry point





                # write back to orders
                result[product] = orders

            # persistence
            traderData = ""

            conversions = 1
            return result, conversions, traderData
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None, 1, state.traderData

class PersistenceData:
    def __init__(self, moving_average_10):
        self.moving_average_10 = moving_average_10