from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict
import numpy as np
import statistics as stat
import math
import json

class Trader:
    def run(self, state: TradingState):
        """
        A stateless advanced trading bot example. Uses:
          1) Fair value calc from the current order depth.
          2) Momentum detection from recent trades.
          3) Simple position limit checks.
          4) Optional usage of observations (e.g., sugarPrice).
        """
        
        print("traderData:", state.traderData)
        print("Observations:", state.observations)

        # Prepare a dictionary to hold orders for each product
        result: Dict[str, List[Order]] = {}

        # Placeholder for demonstration: how you might read an observation
        # E.g., if we want to factor in "sugarPrice" from the first conversionObservations key:
        # (In a real scenario, you'd tailor this logic carefully!)
        sugar_price_factor = 1.0
        if state.observations.conversionObservations:
            # Arbitrarily pick one product to read sugarPrice if it exists
            first_product_key = next(iter(state.observations.conversionObservations.keys()), None)
            if first_product_key is not None:
                conversion_obs = state.observations.conversionObservations[first_product_key]
                sugar_price_factor = max(0.5, min(2.0, conversion_obs.sugarPrice / 100.0))
                # Just an example scaling factor:
                #   if sugarPrice is 100, factor = 1
                #   if sugarPrice is higher, factor > 1
                #   if sugarPrice is lower, factor < 1
        
        # We can define some hypothetical max position for demonstration
        MAX_POSITION = 20

        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []

            # Collect best bid and ask from the current order depth
            if len(order_depth.buy_orders) == 0 or len(order_depth.sell_orders) == 0:
                # If we do not have both sides of the market, skip advanced logic
                result[product] = orders
                continue

            # best_bid is the highest bid price
            best_bid = max(order_depth.buy_orders.keys())
            best_bid_volume = order_depth.buy_orders[best_bid]

            # best_ask is the lowest ask price
            best_ask = min(order_depth.sell_orders.keys())
            best_ask_volume = order_depth.sell_orders[best_ask]

            # Compute a naive fair value
            fair_value = (best_bid + best_ask) / 2

            # Detect momentum from the last few trades
            recent_trades = state.market_trades.get(product, [])
            if not recent_trades:
                momentum_price = fair_value
            else:
                # Take the average of last N trades
                N = 3  # last 3 trades
                last_trades = recent_trades[-N:]
                avg_trade_price = sum([trade.price for trade in last_trades]) / len(last_trades)
                momentum_price = avg_trade_price
            
            # Compare momentum_price vs fair_value
            # If momentum_price > fair_value => uptrend, else downtrend
            # Also factor in the sugar_price_factor we extracted above
            uptrend = (momentum_price * sugar_price_factor) > fair_value

            # Check current position
            current_position = state.position.get(product, 0)

            # Example logic:
            #   - If uptrend and we have space to buy => place a buy near best_ask
            #   - If downtrend and we have inventory => place a sell near best_bid

            # We define how many units we want to trade:
            #   Here, we can do a small portion to illustrate the concept
            trade_size = 5

            # If uptrend, attempt to BUY if we haven't exceeded our max position
            if uptrend and current_position < MAX_POSITION:
                # Place a buy order at best_ask if it's below or near fair value
                if best_ask < fair_value * 1.01:  # allow some slight premium
                    buy_quantity = min(trade_size, MAX_POSITION - current_position)
                    orders.append(Order(product, best_ask, buy_quantity))

            # If downtrend, attempt to SELL if we have a positive position
            if not uptrend and current_position > -MAX_POSITION:
                # Place a sell order at best_bid if it's above or near fair value
                if best_bid > fair_value * 0.99:
                    sell_quantity = min(trade_size, current_position + MAX_POSITION)
                    # Negative quantity => SELL
                    orders.append(Order(product, best_bid, -sell_quantity))

            result[product] = orders

        # This is the updated traderData string we can pass along if needed
        # (Set or update as you wish, or leave as a placeholder.)
        traderData = "ADVANCED_BOT_STATELESS"

        # Conversions placeholder
        conversions = 1

        return result, conversions, traderData
