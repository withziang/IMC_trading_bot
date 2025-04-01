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

                # check arbitrage
                    # two pointers
                sorted_sell = [[key, abs(value)] for key, value in sorted(order_depth.sell_orders.items())]
                sorted_buy = [[key, abs(value)] for key, value in sorted(order_depth.buy_orders.items())]
                if sorted_sell[0][0] < sorted_buy[-1][0]:
                    print("there is no arbitrage")
                else:
                    i = 0  # sell
                    j = 0  # buy
                    while i < len(sorted_sell) and j < len(sorted_buy):
                        # check if sell < buy
                        while j < len(sorted_buy) and (sorted_sell[i][0] >= sorted_buy[j][0] or not sorted_buy[j][1]):
                            j += 1
                        if j < len(sorted_buy) and sorted_sell[i][0] < sorted_buy[j][0]:
                            # we have a trade
                            amount = min(sorted_buy[j][1], sorted_sell[i][1])
                            print(f"we have a trade {sorted_buy[j]} and {sorted_sell[i]} for {amount} amount \n")
                            orders.append(Order(product, sorted_sell[i][0], amount))
                            orders.append(Order(product, sorted_buy[j][0], -amount))
                            sorted_buy[j][1] -= amount
                            sorted_sell[i][1] -= amount
                        if not sorted_sell[i][1]:
                            i += 1


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