from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict
import numpy as np
import statistics as stat
import math

class Trader:

    def __init__(self):
        # Parameters
        self.window_size = 50  # Lookback for moving averages
        self.position_limits = {'AMETHYSTS': 20, 'STARFRUIT': 20}
        self.max_spread_pct = 0.015  # Max spread for market making
        self.volatility_window = 10  # For dynamic risk adjustment
        
        # Data storage
        self.price_history = {}  # Mid-prices over time
        self.spread_history = {}  # Bid-ask spreads
        self.volume_history = {}  # Trade volumes
        self.ema_fast = {}  # Fast EMA (reactive)
        self.ema_slow = {}  # Slow EMA (smoother)
        self.order_imbalance_history = {}  # Tracks buy/sell pressure

    def update_ema(self, product: str, price: float, alpha_fast=0.2, alpha_slow=0.05):
        """Update fast and slow EMAs for trend detection."""
        if product not in self.ema_fast:
            self.ema_fast[product] = price
            self.ema_slow[product] = price
        else:
            self.ema_fast[product] = alpha_fast * price + (1 - alpha_fast) * self.ema_fast[product]
            self.ema_slow[product] = alpha_slow * price + (1 - alpha_slow) * self.ema_slow[product]

    def get_vwap(self, order_depth: OrderDepth) -> float:
        """Volume-Weighted Average Price (VWAP)."""
        total_volume = 0
        total_value = 0
        
        # Sum all buy orders
        for price, vol in order_depth.buy_orders.items():
            total_value += price * abs(vol)
            total_volume += abs(vol)
        
        # Sum all sell orders
        for price, vol in order_depth.sell_orders.items():
            total_value += price * abs(vol)
            total_volume += abs(vol)
        
        return total_value / total_volume if total_volume > 0 else None

    def get_order_imbalance(self, order_depth: OrderDepth) -> float:
        """Measures buy vs sell pressure (-1 to +1)."""
        total_buy = sum(order_depth.buy_orders.values())
        total_sell = abs(sum(order_depth.sell_orders.values()))
        total_volume = total_buy + total_sell
        return (total_buy - total_sell) / total_volume if total_volume > 0 else 0

    def calculate_fair_price(self, product: str, order_depth: OrderDepth) -> float:
        """Combines VWAP, EMA, Bollinger Bands, and Order Imbalance."""
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid_price = (best_bid + best_ask) / 2
        
        # Update price history
        if product not in self.price_history:
            self.price_history[product] = []
        self.price_history[product].append(mid_price)
        
        # Keep window_size most recent prices
        if len(self.price_history[product]) > self.window_size:
            self.price_history[product] = self.price_history[product][-self.window_size:]
        
        # Calculate VWAP
        vwap = self.get_vwap(order_depth) or mid_price
        
        # Update EMAs
        self.update_ema(product, mid_price)
        
        # Bollinger Bands (if enough data)
        sma, std_dev = None, None
        if len(self.price_history[product]) >= 10:
            sma = stat.mean(self.price_history[product])
            std_dev = stat.stdev(self.price_history[product]) if len(self.price_history[product]) > 1 else 0
        
        # Order Imbalance Factor
        imbalance = self.get_order_imbalance(order_depth)
        
        # Combine into fair price (weights can be tuned)
        fair_price = 0.4 * vwap + 0.3 * self.ema_fast[product] + 0.2 * mid_price
        if sma and std_dev:
            # Apply mean reversion if outside Bollinger Bands
            if mid_price > sma + 1.5 * std_dev:
                fair_price *= 0.995  # Slightly reduce fair price (overbought)
            elif mid_price < sma - 1.5 * std_dev:
                fair_price *= 1.005  # Slightly increase (oversold)
        
        # Adjust for order imbalance (more buyers -> higher fair price)
        fair_price *= (1 + imbalance * 0.01)
        
        return fair_price

    def dynamic_spread_adjustment(self, product: str, fair_price: float) -> float:
        """Wider spreads in volatile markets, tighter in stable ones."""
        if len(self.price_history.get(product, [])) < self.volatility_window:
            return self.max_spread_pct / 2  # Default moderate spread
        
        recent_prices = self.price_history[product][-self.volatility_window:]
        returns = np.diff(recent_prices) / recent_prices[:-1]
        volatility = np.std(returns) if len(returns) > 1 else 0
        
        # Wider spread if high volatility
        spread = min(
            self.max_spread_pct,
            0.005 + volatility * 2  # Base spread + volatility adjustment
        )
        return spread

    def calculate_order_size(self, product: str, price: float, fair_price: float, position: int) -> int:
        """Dynamic position sizing based on edge and current exposure."""
        position_limit = self.position_limits.get(product, 20)
        price_diff = (fair_price - price) / fair_price  # % from fair value
        
        # Base size scales with edge and remaining position
        max_size = position_limit - position if price_diff > 0 else position_limit + position
        base_size = min(
            position_limit,
            max(1, int(position_limit * abs(price_diff) * 10))  # Aggressive sizing
        )
        
        # Reduce size if already heavily positioned
        position_pct = abs(position) / position_limit
        size = int(base_size * (1 - position_pct * 0.7))  # Scale down near limits
        
        return min(size, max_size)

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result = {}
        
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            position = state.position.get(product, 0)
            
            # Skip if no liquidity
            if not order_depth.buy_orders or not order_depth.sell_orders:
                continue
            
            # Calculate fair price and volatility-adjusted spread
            fair_price = self.calculate_fair_price(product, order_depth)
            spread = self.dynamic_spread_adjustment(product, fair_price)
            
            # Market Making Orders
            bid_price = round(fair_price * (1 - spread / 2))
            ask_price = round(fair_price * (1 + spread / 2))
            
            bid_size = self.calculate_order_size(product, bid_price, fair_price, position)
            ask_size = self.calculate_order_size(product, ask_price, fair_price, position)
            
            orders = []
            if bid_size > 0:
                orders.append(Order(product, bid_price, bid_size))
            if ask_size > 0:
                orders.append(Order(product, ask_price, -ask_size))
            
            # Aggressive Orders (if mispriced)
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            
            if best_ask < fair_price * 0.995:  # Undervalued
                buy_size = self.calculate_order_size(product, best_ask, fair_price, position)
                orders.append(Order(product, best_ask, buy_size))
            
            if best_bid > fair_price * 1.005:  # Overvalued
                sell_size = self.calculate_order_size(product, best_bid, fair_price, position)
                orders.append(Order(product, best_bid, -sell_size))
            
            result[product] = orders
        
        return result, 0, ""  # No conversions, empty trader_data