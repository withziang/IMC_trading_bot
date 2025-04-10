from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict, Tuple
import math

class Trader:
    def __init__(self):
        # Initialize trader state variables
        self.position_limits = {"KELP": 50,"RAINFOREST_RESIN": 50, "SQUID_INK":50}
        
        # For moving averages and price history
        self.price_history = {}
        self.ema_short = {}  # Short term exponential moving average
        self.ema_long = {}   # Long term exponential moving average
        self.vwap = {}       # Volume weighted average price
        
        # For tracking unfilled orders
        self.previous_orders = {}
        
        # For market making
        self.bid_ask_spread = {}
        
        # For conversion logic
        self.conversion_opportunities = {}

    def run(self, state: TradingState):
        """
        Advanced trading bot using multiple algorithmic strategies based on market data.
        """
        # Initialize results
        result = {}
        conversions = {}
        
        # Parse trader data if available
        if state.traderData and state.traderData != "SAMPLE":
            try:
                # Deserialize any persisted state
                stored_data = eval(state.traderData)
                # Restore price history and other data
                if "price_history" in stored_data:
                    self.price_history = stored_data["price_history"]
                if "ema_short" in stored_data:
                    self.ema_short = stored_data["ema_short"]
                if "ema_long" in stored_data:
                    self.ema_long = stored_data["ema_long"]
            except:
                # Start fresh if there's any issue with the data
                pass
        
        # Update market data for each product
        for product in state.order_depths.keys():
            if product not in self.price_history:
                self.price_history[product] = []
            
            # Calculate mid price if possible
            order_depth = state.order_depths[product]
            mid_price = self.calculate_mid_price(order_depth)
            
            if mid_price:
                # Update price history
                self.price_history[product].append(mid_price)
                # Limit history to prevent memory issues
                if len(self.price_history[product]) > 100:
                    self.price_history[product].pop(0)
                
                # Update technical indicators
                self.update_technical_indicators(product)
        
        # Process each product
        for product in state.order_depths.keys():
            order_depth = state.order_depths[product]
            current_position = state.position.get(product, 0)
            position_limit = self.position_limits.get(product, 100)  # Default limit
            
            # Skip if no orders for this product
            if not order_depth.buy_orders and not order_depth.sell_orders:
                result[product] = []
                continue
            
            # Apply multiple trading strategies and combine their signals
            orders = []
            
            # Strategy 1: Market making (bid-ask spread capture)
            mm_orders = self.market_making_strategy(product, order_depth, current_position, position_limit)
            orders.extend(mm_orders)
            
            # Strategy 2: Momentum trading based on EMAs
            if product in self.ema_short and product in self.ema_long:
                momentum_orders = self.momentum_strategy(product, order_depth, current_position, position_limit)
                orders.extend(momentum_orders)
            
            # Strategy 3: Mean reversion (if applicable)
            if len(self.price_history.get(product, [])) > 20:
                reversion_orders = self.mean_reversion_strategy(product, order_depth, current_position, position_limit)
                orders.extend(reversion_orders)
            
            # Strategy 4: Arbitrage (if applicable)
            if product in state.observations.conversionObservations:
                arb_orders = self.arbitrage_strategy(product, state, current_position)
                orders.extend(arb_orders)
            
            # Apply risk management and position limits
            filtered_orders = self.apply_risk_management(orders, current_position, position_limit)
            
            # Merge orders of the same price
            final_orders = self.merge_orders(filtered_orders)
            result[product] = final_orders
            
            # Prepare conversion opportunities if applicable
            if product in state.observations.conversionObservations:
                conversions = self.calculate_conversions(state, product)
        
        # Persist state for next round
        trader_data = {
            "price_history": self.price_history,
            "ema_short": self.ema_short,
            "ema_long": self.ema_long,
            "timestamp": state.timestamp
        }
        
        return result, conversions, str(trader_data)

    def calculate_mid_price(self, order_depth: OrderDepth) -> float:
        """Calculate the mid price from order book"""
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return None
            
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return (best_bid + best_ask) / 2
    
    def update_technical_indicators(self, product: str):
        """Update technical indicators for the product"""
        prices = self.price_history.get(product, [])
        if len(prices) < 3:
            return
            
        # Calculate Exponential Moving Averages
        short_period = min(8, len(prices))
        long_period = min(21, len(prices))
        
        # Short term EMA (faster reaction)
        if product not in self.ema_short or len(prices) <= short_period:
            self.ema_short[product] = sum(prices[-short_period:]) / short_period
        else:
            multiplier = 2 / (short_period + 1)
            self.ema_short[product] = (prices[-1] - self.ema_short[product]) * multiplier + self.ema_short[product]
        
        # Long term EMA (slower reaction)
        if product not in self.ema_long or len(prices) <= long_period:
            self.ema_long[product] = sum(prices[-long_period:]) / long_period
        else:
            multiplier = 2 / (long_period + 1)
            self.ema_long[product] = (prices[-1] - self.ema_long[product]) * multiplier + self.ema_long[product]
    
    def market_making_strategy(self, product: str, order_depth: OrderDepth, current_position: int, position_limit: int) -> List[Order]:
        """Market making strategy to capture bid-ask spread"""
        orders = []
        
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return orders
            
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        spread = best_ask - best_bid
        
        # Only make markets if spread is sufficiently large
        if spread <= 1:
            return orders
            
        # Calculate bid and ask prices and sizes based on position
        position_ratio = current_position / position_limit if position_limit > 0 else 0
        
        # If we have a large long position, be more aggressive selling and less aggressive buying
        if position_ratio > 0.5:
            # More aggressive selling
            our_ask = best_bid + max(1, round(spread * 0.3))
            our_bid = best_bid + 1
            ask_size = min(position_limit - current_position, max(1, abs(round(order_depth.buy_orders[best_bid] * 0.7))))
            bid_size = max(1, round(abs(order_depth.sell_orders[best_ask]) * 0.3))
        # If we have a large short position, be more aggressive buying and less aggressive selling
        elif position_ratio < -0.5:
            # More aggressive buying
            our_ask = best_ask - 1
            our_bid = best_ask - max(1, round(spread * 0.3))
            ask_size = max(1, round(abs(order_depth.buy_orders[best_bid]) * 0.3))
            bid_size = min(position_limit + current_position, max(1, abs(round(order_depth.sell_orders[best_ask] * 0.7))))
        # Balanced position, make markets both ways
        else:
            our_bid = best_bid + 1
            our_ask = best_ask - 1
            bid_size = max(1, abs(round(order_depth.sell_orders[best_ask] * 0.5)))
            ask_size = max(1, abs(round(order_depth.buy_orders[best_bid] * 0.5)))
        
        # Ensure position limits aren't exceeded
        bid_size = min(bid_size, position_limit + current_position)
        ask_size = min(ask_size, position_limit - current_position)
        
        if bid_size > 0:
            orders.append(Order(product, our_bid, bid_size))
        if ask_size > 0:
            orders.append(Order(product, our_ask, -ask_size))
            
        return orders
    
    def momentum_strategy(self, product: str, order_depth: OrderDepth, current_position: int, position_limit: int) -> List[Order]:
        """Momentum trading strategy based on EMA crossovers"""
        orders = []
        
        # Check if we have enough data
        if product not in self.ema_short or product not in self.ema_long:
            return orders
            
        short_ema = self.ema_short[product]
        long_ema = self.ema_long[product]
        
        # Calculate signal strength based on EMA difference
        signal = (short_ema - long_ema) / long_ema if long_ema > 0 else 0
        
        # Strong buy signal: short EMA above long EMA
        if signal > 0.01 and current_position < position_limit * 0.8:
            # Buy at slightly above the best bid
            if order_depth.buy_orders:
                best_bid = max(order_depth.buy_orders.keys())
                # Size based on signal strength and available quantity
                quantity = min(
                    position_limit - current_position,
                    max(1, abs(int(signal * 10 * order_depth.buy_orders[best_bid])))
                )
                if quantity > 0:
                    orders.append(Order(product, best_bid + 1, quantity))
                    
        # Strong sell signal: short EMA below long EMA
        elif signal < -0.01 and current_position > -position_limit * 0.8:
            # Sell at slightly below the best ask
            if order_depth.sell_orders:
                best_ask = min(order_depth.sell_orders.keys())
                # Size based on signal strength and available quantity
                quantity = min(
                    position_limit + current_position,
                    max(1, abs(int(signal * 10 * order_depth.sell_orders[best_ask])))
                )
                if quantity > 0:
                    orders.append(Order(product, best_ask - 1, -quantity))
                    
        return orders
        
    def mean_reversion_strategy(self, product: str, order_depth: OrderDepth, current_position: int, position_limit: int) -> List[Order]:
        """Mean reversion strategy based on price deviations from average"""
        orders = []
        prices = self.price_history.get(product, [])
        
        if len(prices) < 20:
            return orders
            
        # Calculate recent average price
        avg_price = sum(prices[-20:]) / 20
        
        # Calculate standard deviation
        variance = sum((p - avg_price) ** 2 for p in prices[-20:]) / 20
        std_dev = math.sqrt(variance) if variance > 0 else 0
        
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return orders
            
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid_price = (best_bid + best_ask) / 2
        
        # Reversion signal based on z-score (how many standard deviations from mean)
        if std_dev > 0:
            z_score = (mid_price - avg_price) / std_dev
            
            # If price is significantly above average, sell
            if z_score > 1.5 and current_position > -position_limit * 0.9:
                quantity = min(
                    position_limit + current_position,
                    abs(round(z_score * 5))
                )
                if quantity > 0:
                    orders.append(Order(product, best_bid, -quantity))
            
            # If price is significantly below average, buy
            elif z_score < -1.5 and current_position < position_limit * 0.9:
                quantity = min(
                    position_limit - current_position,
                    abs(round(z_score * 5))
                )
                if quantity > 0:
                    orders.append(Order(product, best_ask, quantity))
                    
        return orders
        
    def arbitrage_strategy(self, product: str, state: TradingState, current_position: int) -> List[Order]:
        """Identify arbitrage opportunities based on conversion rates"""
        orders = []
        
        # This is a simplified placeholder for arbitrage logic
        # In a real implementation, this would examine conversion rates between related products
        
        # Example for PINA_COLADA which might be convertible to/from COCONUT and PINEAPPLE
        if product == "PINA_COLADA" and "COCONUT" in state.order_depths and "PINEAPPLE" in state.order_depths:
            # Check for profitable conversions (simplified example)
            pina_mid = self.calculate_mid_price(state.order_depths[product])
            coconut_mid = self.calculate_mid_price(state.order_depths["COCONUT"]) 
            pineapple_mid = self.calculate_mid_price(state.order_depths["PINEAPPLE"])
            
            if pina_mid and coconut_mid and pineapple_mid:
                # Hypothetical conversion formula (would need actual conversion rates)
                conversion_value = coconut_mid + pineapple_mid
                
                # If PINA_COLADA is trading higher than its components, sell PINA and buy components
                if pina_mid > conversion_value * 1.02:  # 2% profit threshold
                    # Logic to add arbitrage orders
                    pass
                    
                # If PINA_COLADA is trading lower than its components, buy PINA and sell components
                elif pina_mid < conversion_value * 0.98:  # 2% profit threshold
                    # Logic to add arbitrage orders
                    pass
                    
        return orders
        
    def apply_risk_management(self, orders: List[Order], current_position: int, position_limit: int) -> List[Order]:
        """Apply risk management rules to filter orders"""
        filtered_orders = []
        
        # Track potential position changes from these orders
        potential_position = current_position
        
        for order in orders:
            # Calculate new position if this order executes
            new_position = potential_position + order.quantity
            
            # Check if new position would exceed limits
            if abs(new_position) <= position_limit:
                filtered_orders.append(order)
                potential_position = new_position
            else:
                # Adjust the order to respect position limits
                adjusted_quantity = position_limit - potential_position if order.quantity > 0 else -position_limit - potential_position
                if adjusted_quantity != 0:
                    filtered_orders.append(Order(order.symbol, order.price, adjusted_quantity))
                    potential_position += adjusted_quantity
                    
        return filtered_orders
        
    def merge_orders(self, orders: List[Order]) -> List[Order]:
        """Merge orders at the same price level"""
        price_quantities = {}
        
        for order in orders:
            if order.price in price_quantities:
                price_quantities[order.price] += order.quantity
            else:
                price_quantities[order.price] = order.quantity
                
        merged_orders = []
        for price, quantity in price_quantities.items():
            if quantity != 0:  # Skip orders that would cancel out
                merged_orders.append(Order(orders[0].symbol, price, quantity))
                
        return merged_orders
        
    def calculate_conversions(self, state: TradingState, product: str) -> Dict:
        """Calculate potential conversion opportunities"""
        # This is a placeholder for conversion logic
        # In a real implementation, this would calculate profitable conversions
        return {}