from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string

class Trader:
    
    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))

                # Orders to be placed on exchange matching engine
        result = {}
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            if product not in ['SQUID_INK', 'KELP']:
                continue

            acceptable_price = { # sell price
                    'SQUID_INK' : 2100,
                    'KELP': 2028
            }
            acceptable_buy = {  # buy
                    'SQUID_INK' : 2050,
                    'KELP' : 2020
            }

                    # Participant should calculate this value
            # print("Acceptable price : " + str(acceptable_price))
            print("Buy Order depth : " + str(len(order_depth.buy_orders)) + ", Sell order depth : " + str(len(order_depth.sell_orders)))
            print(f"trading product {product}")

            if len(order_depth.sell_orders) != 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
                best_ask_amount = max(best_ask_amount,50)
                if int(best_ask) < acceptable_buy[product]:
                    print("BUY", str(-best_ask_amount) + "x", best_ask)
                    orders.append(Order(product, best_ask, -best_ask_amount))
    
            if len(order_depth.buy_orders) != 0:
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
                best_bid_amount = max(best_bid_amount,50)
                if int(best_bid) > acceptable_price[product]:
                    print("SELL", str(best_bid_amount) + "x", best_bid)
                    orders.append(Order(product, best_bid, -best_bid_amount))
            
            result[product] = orders
    
            # String value holding Trader state data required. 
                # It will be delivered as TradingState.traderData on next execution.
        traderData = "SAMPLE" 
        
                # Sample conversion request. Check more details below. 
        conversions = 1
        return result, conversions, traderData