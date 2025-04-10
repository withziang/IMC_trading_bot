from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import pandas as pd
import numpy as np
import statistics
import math

class Trader:

    def run(self, state: TradingState):
        # Advanced Trading Bot using technical indicators and risk management

        orders = {}  # Dictionary to store orders for each product
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders[product] = []  # Initialize list of orders for the current product

            # 1. Data Preparation and Feature Engineering

            # Order book data
            buy_prices, buy_sizes = zip(*order_depth.buy_orders.items()) if order_depth.buy_orders else ([], [])
            sell_prices, sell_sizes = zip(*order_depth.sell_orders.items()) if order_depth.sell_orders else ([], [])

            # Calculate midpoint (average of best bid and ask)
            best_bid = max(buy_prices) if buy_prices else 0
            best_ask = min(sell_prices) if sell_prices else float('inf')
            midpoint = (best_bid + best_ask) / 2 if buy_prices and sell_prices else 0

            # Create a Pandas DataFrame for analysis
            data = {
                'buy_price': buy_prices,
                'buy_size': buy_sizes,
                'sell_price': sell_prices,
                'sell_size': sell_sizes,
                'midpoint': [midpoint] * max(len(buy_prices), len(sell_prices)) if max(len(buy_prices), len(sell_prices)) > 0 else []
            }
            df = pd.DataFrame(data)


            # 2. Technical Indicator Calculation
            period = 10 #adjust based on the product
            # Simple Moving Average (SMA)
            df['sma'] = df['midpoint'].rolling(window=period).mean()

            # Exponential Moving Average (EMA)
            df['ema'] = df['midpoint'].ewm(span=period, adjust=False).mean()

            # Moving Average Convergence Divergence (MACD)
            df['macd'] = df['ema'].ewm(span=12, adjust=False).mean() - df['ema'].ewm(span=26, adjust=False).mean()
            df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()


            # Relative Strength Index (RSI)
            delta = df['midpoint'].diff()
            up, down = delta.copy(), delta.copy()
            up[up < 0] = 0
            down[down > 0] = 0
            roll_up1 = up.ewm(span=14, adjust=False).mean()
            roll_down1 = np.abs(down.ewm(span=14, adjust=False).mean())
            RS = roll_up1 / roll_down1
            df['rsi'] = 100.0 - (100.0 / (1.0 + RS))


            #Bollinger Bands
            df['typical_price'] = (best_ask + best_bid + df['midpoint'].mean()) / 3 if (best_ask != float('inf') and best_bid != 0) else 0
            df['stddev'] = df['typical_price'].rolling(window=period).std()
            df['upper_band'] = df['sma'] + 2 * df['stddev']
            df['lower_band'] = df['sma'] - 2 * df['stddev']


            # 3. Trading Logic (Sophisticated with Multiple Indicators)
            position_limit = 10 #Risk management, adjust as needed based on the product
            current_position = state.position.get(product, 0) #Gets current Position
            last_row = df.iloc[-1] if not df.empty else None
            if last_row is not None:
                if (last_row['rsi'] < 30 and current_position < position_limit and best_ask != float('inf')):  # Oversold, buy
                    quantity_to_buy = min(position_limit - current_position, buy_sizes[0] if buy_sizes else position_limit) #check for buy_sizes available
                    orders[product].append(Order(product, best_ask, quantity_to_buy))
                    print(f"BUY {quantity_to_buy} x {best_ask} of {product} based on RSI.")
                elif (last_row['rsi'] > 70 and current_position > -position_limit and best_bid != 0):  # Overbought, sell
                    quantity_to_sell = min(current_position + position_limit, sell_sizes[0] if sell_sizes else position_limit) #check for sell_sizes
                    orders[product].append(Order(product, best_bid, -quantity_to_sell))
                    print(f"SELL {quantity_to_sell} x {best_bid} of {product} based on RSI.")
                elif (last_row['macd'] > last_row['signal'] and current_position < position_limit and best_ask != float('inf')):
                    quantity_to_buy = min(position_limit - current_position, buy_sizes[0] if buy_sizes else position_limit) #check for buy_sizes available
                    orders[product].append(Order(product, best_ask, quantity_to_buy))
                    print(f"BUY {quantity_to_buy} x {best_ask} of {product} based on MACD.")
                elif (last_row['macd'] < last_row['signal'] and current_position > -position_limit and best_bid != 0):
                    quantity_to_sell = min(current_position + position_limit, sell_sizes[0] if sell_sizes else position_limit) #check for sell_sizes
                    orders[product].append(Order(product, best_bid, -quantity_to_sell))
                    print(f"SELL {quantity_to_sell} x {best_bid} of {product} based on MACD.")
                elif (df['midpoint'][-1] < last_row['lower_band'] and current_position < position_limit and best_ask != float('inf')):
                    quantity_to_buy = min(position_limit - current_position, buy_sizes[0] if buy_sizes else position_limit) #check for buy_sizes available
                    orders[product].append(Order(product, best_ask, quantity_to_buy))
                    print(f"BUY {quantity_to_buy} x {best_ask} of {product} based on Bollinger Bands.")
                elif (df['midpoint'][-1] > last_row['upper_band'] and current_position > -position_limit and best_bid != 0):
                     quantity_to_sell = min(current_position + position_limit, sell_sizes[0] if sell_sizes else position_limit) #check for sell_sizes
                     orders[product].append(Order(product, best_bid, -quantity_to_sell))
                     print(f"SELL {quantity_to_sell} x {best_bid} of {product} based on Bollinger Bands.")



        # 4. Trader Data (Maintaining State)
        traderData = "Advanced Trading Bot"  # Example, can be expanded to store more information
        conversions = 1 #Default
        return orders, conversions, traderData