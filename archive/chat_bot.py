from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string
import statistics as stat
import numpy as np
import jsonpickle

class Trader:

    def run(self, state: TradingState):
        orders = {}

        # Loop over each product in the market
        for product, order_depth in state.order_depths.items():
            orders[product] = []
            
            # Get best bid and ask from order depth, if available
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

            # Compute mid price
            if best_bid is not None and best_ask is not None:
                mid_price = (best_bid + best_ask) / 2
            elif best_bid is not None:
                mid_price = best_bid
            elif best_ask is not None:
                mid_price = best_ask
            else:
                # If no orders exist, skip this product
                continue

            # Calculate volume totals and weighted average prices
            total_buy_volume = sum(order_depth.buy_orders.values())
            total_sell_volume = sum(order_depth.sell_orders.values())

            weighted_bid = (sum(price * qty for price, qty in order_depth.buy_orders.items()) /
                            total_buy_volume) if total_buy_volume > 0 else best_bid
            weighted_ask = (sum(price * qty for price, qty in order_depth.sell_orders.items()) /
                            total_sell_volume) if total_sell_volume > 0 else best_ask

            # Determine volume imbalance (normalized difference between buy and sell volumes)
            imbalance = (total_buy_volume - total_sell_volume) / (total_buy_volume + total_sell_volume + 1e-6)

            # Adjust the mid price based on the imbalance (e.g., a 10% modulation factor)
            advanced_price = mid_price * (1 + 0.1 * imbalance)

            # Incorporate momentum from recent market trades if available
            recent_trades = state.market_trades.get(product, [])
            if recent_trades:
                # Use last 5 trades (or all if less than 5) for momentum calculation
                recent_prices = [trade.price for trade in recent_trades[-5:] if trade.price > 0]
                if recent_prices:
                    average_recent_price = sum(recent_prices) / len(recent_prices)
                    # Momentum factor as percentage difference from the average recent price
                    momentum = (mid_price - average_recent_price) / mid_price
                    # Adjust the advanced price slightly using momentum (5% sensitivity)
                    advanced_price *= (1 + 0.05 * momentum)

            # Define a threshold based on the mid price (2% here)
            threshold = 0.02 * mid_price

            # Decision making:
            # If the best ask is significantly lower than our advanced price, we consider buying.
            if best_ask is not None and (advanced_price - best_ask) > threshold:
                # Buy the full available ask quantity (convert to a positive order quantity)
                buy_qty = -order_depth.sell_orders[best_ask]
                orders[product].append(Order(product, best_ask, buy_qty))
                print(f"Product: {product} | BUY {buy_qty} @ {best_ask}")

            # If the best bid is significantly higher than our advanced price, we consider selling.
            if best_bid is not None and (best_bid - advanced_price) > threshold:
                # Sell the full available bid quantity (convert to a negative order quantity)
                sell_qty = -order_depth.buy_orders[best_bid]
                orders[product].append(Order(product, best_bid, sell_qty))
                print(f"Product: {product} | SELL {sell_qty} @ {best_bid}")

        # Update trader state (a string that can hold any state info required)
        traderData = "ADVANCED_TRADER_STATE"
        # Conversions variable (if needed in the larger system) is set to 1 for now
        conversions = 1

        return orders, conversions, traderData
