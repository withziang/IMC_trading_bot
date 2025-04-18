from datamodel import OrderDepth, UserId, TradingState, Order
import json
import math
import statistics
from typing import Dict, List, Any
import collections
import numpy as np
import jsonpickle



# Helper class for storing persistent data
class PersistenceData:
    def __init__(self, macaron_price_history=None):
        # Use deque for efficient rolling window
        self.macaron_price_history = collections.deque(macaron_price_history if macaron_price_history else [], maxlen=20) # Store last 20 prices for SMA

    def to_json(self) -> str:
        # Convert deque to list for JSON serialization
        data = {'macaron_price_history': list(self.macaron_price_history)}
        return jsonpickle.encode(data)

    @staticmethod
    def from_json(json_str: str):
        if not json_str:
            return PersistenceData()
        try:
            data = jsonpickle.decode(json_str)
            # Recreate deque from the loaded list
            return PersistenceData(macaron_price_history=data.get('macaron_price_history', []))
        except Exception as e:
            print(f"Error decoding traderData: {e}")
            return PersistenceData() # Return default if decoding fails


class Trader:
    MACARON_SYMBOL = "MAGNIFICENT_MACARONS"
    MACARON_POSITION_LIMIT = 75
    # Critical Sunlight Index - This is a HYPOTHESIS and might need tuning!
    # Let's start with a value. Observe results and adjust if possible.
    CRITICAL_SUNLIGHT_INDEX = 3800 # Example value, adjust based on observation

    def __init__(self):
        # Initialize any state needed, like the persistence object
        self.persisted_data = PersistenceData()
        print("Trader Initialized")

    def calculate_weighted_average_price(self, order_depth: OrderDepth) -> float | None:
        """Calculates the weighted average price from order depth."""
        # Call get_best_bid_ask ONCE and unpack all four values
        best_bid, best_ask, best_bid_vol, best_ask_vol = self.get_best_bid_ask(order_depth)

        # Now use these variables directly in the calculation
        # Ensure volumes are non-zero before calculation
        if best_bid is not None and best_ask is not None and best_bid_vol != 0 and best_ask_vol != 0:
            # Remember sell volumes (best_ask_vol) are negative, use abs() for weighting
            wap = (best_bid * abs(best_ask_vol) + best_ask * abs(best_bid_vol)) / (abs(best_bid_vol) + abs(best_ask_vol))
            return wap
        elif best_bid is not None and best_bid_vol != 0:
            # Fallback if only valid bids exist
            return best_bid
        elif best_ask is not None and best_ask_vol != 0:
             # Fallback if only valid asks exist
            return best_ask
        else:
            # Return None if not enough data for WAP or fallbacks
            return None

    def get_best_bid_ask(self, order_depth: OrderDepth) -> tuple[int | None, int | None, int | None, int | None]:
        """Extracts best bid and ask price and volume."""
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        best_bid_vol = order_depth.buy_orders.get(best_bid, 0) if best_bid is not None else 0

        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
        best_ask_vol = order_depth.sell_orders.get(best_ask, 0) if best_ask is not None else 0 # Sell volumes are negative

        return best_bid, best_ask, best_bid_vol, best_ask_vol

    def get_current_position(self, state: TradingState, product: str) -> int:
        """Safely gets the current position for a product."""
        return state.position.get(product, 0)

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        """
        Takes all buy and sell orders for all symbols as input,
        and outputs a list of orders to be sent.
        """
        print(f"\n--- Timestamp: {state.timestamp} ---")
        # Decode persisted data
        self.persisted_data = PersistenceData.from_json(state.traderData)
        print(f"Trader Data (decoded): {self.persisted_data.to_json()}")
        #print(f"Observations: {state.observations}") # Can be very verbose
        print(f"Positions: {state.position}")

        result: Dict[str, List[Order]] = {} # Orders to place for each symbol
        conversions = 0 # No conversions implemented yet

        # --- MACARON Trading Logic ---
        product = self.MACARON_SYMBOL
        if product in state.order_depths and product in state.observations.conversionObservations:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            current_position = self.get_current_position(state, product)
            obs = state.observations.conversionObservations[product]
            sunlight_index = obs.sunlightIndex

            print(f"MACARONS - Sunlight Index: {sunlight_index}, Current Position: {current_position}")

            # Calculate current market price indicators
            best_bid, best_ask, best_bid_vol, best_ask_vol = self.get_best_bid_ask(order_depth)
            wap = self.calculate_weighted_average_price(order_depth)
            mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else wap

            # Update price history for SMA calculation
            if mid_price is not None:
                self.persisted_data.macaron_price_history.append(mid_price)

            # Calculate Simple Moving Average (SMA) if enough data exists
            sma = None
            if len(self.persisted_data.macaron_price_history) >= 10: # Use 10 periods for SMA
                 sma = statistics.mean(self.persisted_data.macaron_price_history)
                 print(f"MACARONS - WAP: {wap:.2f}, Mid: {mid_price:.2f}, SMA(10): {sma:.2f}")
            elif mid_price is not None:
                 print(f"MACARONS - WAP: {wap:.2f}, Mid: {mid_price:.2f}, (SMA requires more data: {len(self.persisted_data.macaron_price_history)}/10)")
            else:
                 print("MACARONS - No valid market prices available.")


            # === Strategy Implementation ===
            if sunlight_index < self.CRITICAL_SUNLIGHT_INDEX:
                # --- Below CSI: Expect prices to RISE - Go Long ---
                print(f"ACTION: Below CSI ({sunlight_index} < {self.CRITICAL_SUNLIGHT_INDEX}). Targeting LONG position.")

                # Aggressive Buying: Aim to buy up to the position limit
                buy_volume_needed = self.MACARON_POSITION_LIMIT - current_position
                if buy_volume_needed > 0:
                    # Place buy orders aggressively, maybe slightly above best bid or near ask
                    # Simple approach: Place order at best ask if available, otherwise slightly above best bid
                    target_buy_price = best_ask if best_ask is not None else (best_bid + 1 if best_bid is not None else None)

                    if target_buy_price is not None:
                         # Limit order size per tick to avoid excessive risk/market impact
                        order_quantity = min(buy_volume_needed, 10) # Buy in chunks of 10
                        print(f"Placing BUY Order: {order_quantity} @ {target_buy_price}")
                        orders.append(Order(product, target_buy_price, order_quantity))
                    else:
                        print("No suitable buy price found (market thin?).")
                else:
                    print("Already at or above max long position limit.")
                # Avoid selling unless significantly over limit (shouldn't happen with checks)


            else:
                # --- Above or Equal CSI: Prices around Fair Value - Market Making/Mean Reversion ---
                print(f"ACTION: Above/Equal CSI ({sunlight_index} >= {self.CRITICAL_SUNLIGHT_INDEX}). Market Making around Fair Value.")

                # Use SMA as fair value estimate if available, otherwise WAP/Mid-price
                fair_value = sma if sma is not None else wap if wap is not None else mid_price

                if fair_value is not None:
                    print(f"Using Fair Value: {fair_value:.2f}")
                    spread = 1 # Desired half-spread around fair value

                    # --- Place Buy Orders ---
                    buy_price = math.floor(fair_value - spread)
                    buy_volume_allowed = self.MACARON_POSITION_LIMIT - current_position
                    if buy_volume_allowed > 0:
                        # Place buy orders below fair value
                        order_quantity = min(buy_volume_allowed, 10) # Trade in chunks
                        print(f"Placing BUY Order: {order_quantity} @ {buy_price}")
                        orders.append(Order(product, buy_price, order_quantity))
                    else:
                        print("Max long position limit reached, no buy orders.")

                    # --- Place Sell Orders ---
                    sell_price = math.ceil(fair_value + spread)
                    sell_volume_allowed = current_position - (-self.MACARON_POSITION_LIMIT) # Note: limit is symmetric +/- 75
                    if sell_volume_allowed > 0:
                         # Place sell orders above fair value
                        order_quantity = min(sell_volume_allowed, 10) # Trade in chunks
                        print(f"Placing SELL Order: {order_quantity} @ {sell_price}")
                        orders.append(Order(product, sell_price, -order_quantity)) # Negative quantity for sell
                    else:
                        print("Max short position limit reached, no sell orders.")

                else:
                    print("Cannot determine Fair Value, skipping Market Making.")


            result[product] = orders

        # Serialize persistent data
        traderData = self.persisted_data.to_json()
        print(f"Trader Data (encoded): {traderData}")
        print(f"Orders Sent: {result}")
        print(f"Conversions Sent: {conversions}")
        print(f"--- End Timestamp: {state.timestamp} ---")

        return result, conversions, traderData
