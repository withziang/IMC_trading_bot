from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict
import numpy as np
import statistics as stat
import math
import jsonpickle

class Trader:
    
    def __init__(self):
        # Parameters
        self.window_size = 20  # For moving averages and statistical calculations
        self.position_limits = {'AMETHYSTS': 20, 'STARFRUIT': 20}
        self.risk_adjustment = 0.5
        self.max_spread_pct = 0.02  # Maximum acceptable spread percentage
        
        # Data storage
        self.historical_prices = {}  # Stores historical prices for each product
        self.ema_short = {}  # Short-term EMA (fast)
        self.ema_long = {}  # Long-term EMA (slow)
        self.spread_history = {}  # Tracks bid-ask spreads
        self.volume_history = {}  # Tracks trading volume
        
    def update_emas(self, product: str, current_price: float):
        """Update exponential moving averages using only basic math"""
        if product not in self.ema_short:
            self.ema_short[product] = current_price
            self.ema_long[product] = current_price
        else:
            # Short-term EMA (faster reaction)
            self.ema_short[product] = 0.2 * current_price + 0.8 * self.ema_short[product]
            # Long-term EMA (slower reaction)
            self.ema_long[product] = 0.05 * current_price + 0.95 * self.ema_long[product]
    
    def calculate_vwap(self, order_depth: OrderDepth) -> float:
        """Calculate Volume Weighted Average Price without pandas"""
        total_volume = 0
        total_value = 0
        
        for price, volume in order_depth.buy_orders.items():
            total_value += price * abs(volume)
            total_volume += abs(volume)
            
        for price, volume in order_depth.sell_orders.items():
            total_value += price * abs(volume)
            total_volume += abs(volume)
            
        return total_value / total_volume if total_volume > 0 else None
    
    def calculate_fair_price(self, product: str, order_depth: OrderDepth) -> float:
        """Calculate fair price using multiple indicators"""
        if len(order_depth.sell_orders) == 0 or len(order_depth.buy_orders) == 0:
            return None
            
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid_price = (best_bid + best_ask) / 2
        
        # Update historical prices
        if product not in self.historical_prices:
            self.historical_prices[product] = []
        self.historical_prices[product].append(mid_price)
        
        # Keep only the most recent prices
        if len(self.historical_prices[product]) > self.window_size:
            self.historical_prices[product] = self.historical_prices[product][-self.window_size:]
        
        # Calculate VWAP
        vwap = self.calculate_vwap(order_depth)
        if vwap is None:
            vwap = mid_price
            
        # Update EMAs
        self.update_emas(product, mid_price)
        
        # Calculate statistical indicators
        sma = None
        std_dev = None
        if len(self.historical_prices[product]) >= self.window_size:
            sma = stat.mean(self.historical_prices[product])
            std_dev = stat.stdev(self.historical_prices[product]) if len(self.historical_prices[product]) > 1 else 0
            
        # Combine indicators (weighted average)
        if sma is not None and std_dev is not None:
            # Bollinger Bands mean reversion factor
            upper_band = sma + 2 * std_dev
            lower_band = sma - 2 * std_dev
            
            if mid_price > upper_band:
                mean_reversion_factor = -0.1
            elif mid_price < lower_band:
                mean_reversion_factor = 0.1
            else:
                mean_reversion_factor = 0
                
            # Include SMA in fair price calculation
            fair_price = 0.3 * mid_price + 0.3 * vwap + 0.2 * self.ema_short[product] + 0.2 * sma
            fair_price *= (1 + mean_reversion_factor)
        else:
            # Not enough data yet, use simpler calculation
            fair_price = 0.5 * mid_price + 0.3 * vwap + 0.2 * self.ema_short[product]
            
        # Trend adjustment based on EMA crossover
        trend_strength = (self.ema_short[product] - self.ema_long[product]) / self.ema_long[product]
        fair_price *= (1 + min(max(trend_strength * 2, -0.1), 0.1))  # Cap trend adjustment at ±10%
        
        return fair_price
    
    def calculate_spread_stats(self, product: str, order_depth: OrderDepth):
        """Calculate spread statistics and update history"""
        if len(order_depth.sell_orders) == 0 or len(order_depth.buy_orders) == 0:
            return None, None
            
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        current_spread = best_ask - best_bid
        spread_pct = current_spread / best_bid if best_bid > 0 else 0
        
        # Update spread history
        if product not in self.spread_history:
            self.spread_history[product] = []
        self.spread_history[product].append(spread_pct)
        
        # Keep only recent spreads
        if len(self.spread_history[product]) > self.window_size:
            self.spread_history[product] = self.spread_history[product][-self.window_size:]
            
        # Calculate average spread
        avg_spread = stat.mean(self.spread_history[product]) if self.spread_history[product] else 0
        
        return current_spread, avg_spread
    
    def calculate_order_quantity(self, product: str, price: float, fair_price: float, 
                               position: int, position_limit: int) -> int:
        """Smart position sizing with risk management"""
        price_diff = price - fair_price
        price_diff_pct = abs(price_diff) / fair_price
        
        # Base quantity scales with price discrepancy and available position
        max_possible = position_limit - position if price_diff < 0 else position_limit + position
        base_qty = min(position_limit, max(1, int(position_limit * price_diff_pct * 3)))
        
        # Position-based adjustment
        position_pct = abs(position) / position_limit
        if (price_diff < 0 and position >= 0) or (price_diff > 0 and position <= 0):
            # Adding to favorable position
            adj_qty = int(base_qty * (1 + position_pct * 0.5))
        else:
            # Reducing or reversing position
            adj_qty = int(base_qty * (1 - position_pct * 0.75))
            
        return min(adj_qty, max_possible)
    
    def market_make(self, product: str, fair_price: float, position: int, position_limit: int, spread_pct: float):
        """Market making strategy with dynamic spread adjustment"""
        orders = []
        
        # Calculate dynamic spread based on volatility
        if len(self.historical_prices.get(product, [])) >= 5:
            recent_prices = self.historical_prices[product][-5:]
            volatility = stat.stdev(recent_prices) / stat.mean(recent_prices) if len(recent_prices) > 1 else 0
        else:
            volatility = 0
            
        # Adjust spread based on volatility and position
        position_factor = 1 + (abs(position) / position_limit) * 0.5
        dynamic_spread = max(0.005, min(self.max_spread_pct, spread_pct * 0.5 + volatility * 2)) * position_factor
        
        # Calculate bid and ask prices
        bid_price = round(fair_price * (1 - dynamic_spread/2))
        ask_price = round(fair_price * (1 + dynamic_spread/2))
        
        # Calculate order quantities with position adjustment
        bid_qty = self.calculate_order_quantity(product, bid_price, fair_price, position, position_limit)
        ask_qty = self.calculate_order_quantity(product, ask_price, fair_price, position, position_limit)
        
        # Create orders
        if bid_qty > 0:
            orders.append(Order(product, bid_price, bid_qty))
        if ask_qty > 0:
            orders.append(Order(product, ask_price, -ask_qty))
            
        return orders
    
    def run(self, state: TradingState):
        result = {}
        conversions = 0
        trader_data = ""
        
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            position = state.position.get(product, 0)
            position_limit = self.position_limits.get(product, 20)
            
            # Calculate fair price and spread statistics
            fair_price = self.calculate_fair_price(product, order_depth)
            current_spread, avg_spread = self.calculate_spread_stats(product, order_depth)
            
            if fair_price is None or current_spread is None:
                continue  # Skip if no valid data
                
            # Market making strategy
            orders = self.market_make(product, fair_price, position, position_limit, avg_spread or 0.01)
            
            # Add aggressive orders when price is far from fair value
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else 0
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else 0
            
            if best_ask < fair_price * 0.995:  # Good buying opportunity
                buy_qty = self.calculate_order_quantity(product, best_ask, fair_price, position, position_limit)
                orders.append(Order(product, best_ask, buy_qty))
                
            if best_bid > fair_price * 1.005:  # Good selling opportunity
                sell_qty = self.calculate_order_quantity(product, best_bid, fair_price, position, position_limit)
                orders.append(Order(product, best_bid, -sell_qty))
            
            result[product] = orders
        
        return result, conversions, trader_data