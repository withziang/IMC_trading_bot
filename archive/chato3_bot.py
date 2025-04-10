from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict
import numpy as np
import statistics as stat
import math

class Trader:

    def run(self, state: TradingState):
        # Initialize result dictionary for orders per product.
        result = {}

        # Process each product in the order depth.
        for product, order_depth in state.order_depths.items():
            buy_orders = order_depth.buy_orders  # Dict[int, int] with price: quantity (buy side)
            sell_orders = order_depth.sell_orders  # Dict[int, int] with price: quantity (sell side)
            orders = []

            # Check if both sides of the book have orders to compute a mid-price.
            if buy_orders and sell_orders:
                best_bid = max(buy_orders.keys())
                best_ask = min(sell_orders.keys())
                mid_price = (best_bid + best_ask) / 2.0
            elif buy_orders:
                # Fallback: use best bid if no sell orders
                best_bid = max(buy_orders.keys())
                mid_price = best_bid
            elif sell_orders:
                # Fallback: use best ask if no buy orders
                best_ask = min(sell_orders.keys())
                mid_price = best_ask
            else:
                # No order book data available for this product.
                mid_price = None

            # Advanced analysis: use recent market trades to compute a weighted average price (VWAP)
            signal = 0  # +1 for buy, -1 for sell, 0 for no action
            if product in state.market_trades and state.market_trades[product]:
                trades = state.market_trades[product]
                total_quantity = sum(trade.quantity for trade in trades if trade.quantity != 0)
                # Compute VWAP if we have trade volume.
                if total_quantity > 0 and mid_price is not None:
                    vwap = sum(trade.price * trade.quantity for trade in trades) / total_quantity

                    # Generate signal: if current mid-price is lower than VWAP,
                    # it suggests upward momentum (buy signal); if higher, sell signal.
                    if mid_price < vwap * 0.995:  # Adding a small threshold to filter noise
                        signal = +1
                    elif mid_price > vwap * 1.005:
                        signal = -1

            # Decision making based on signal and available order book depth.
            # In a real-world scenario, more risk management and position sizing would be applied.
            if signal == +1 and sell_orders:
                # Buy from the sell side at the best ask price.
                best_ask_price = min(sell_orders.keys())
                ask_quantity = sell_orders[best_ask_price]
                # Place a buy order for the available quantity.
                orders.append(Order(product, best_ask_price, abs(ask_quantity)))
            elif signal == -1 and buy_orders:
                # Sell into the buy side at the best bid price.
                best_bid_price = max(buy_orders.keys())
                bid_quantity = buy_orders[best_bid_price]
                # Place a sell order for the available quantity.
                orders.append(Order(product, best_bid_price, -abs(bid_quantity)))
            else:
                # If no clear signal, the bot might choose to place no orders or use a market-making strategy.
                # Here, we simply pass.
                pass

            # Update result with orders for this product.
            result[product] = orders

        # traderData can be used to hold state information for the next run (if needed)
        traderData = "ADVANCED_TRADER_STATE"
        conversions = 1

        return result, conversions, traderData
