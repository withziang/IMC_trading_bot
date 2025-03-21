


dict_sell = {1:311, 2:123}
dict_buy = {1:311, 2:123, 3: 222}


sorted_sell = [[key, value] for key, value in sorted(dict_sell.items())]
sorted_buy = [[key, value] for key, value in sorted(dict_buy.items())]

i = 0 # sell
j = 0 # buy
while i < len(sorted_sell) and j < len(sorted_buy):
    # check if sell < buy
    while j < len(sorted_buy) and (sorted_sell[i][0] >= sorted_buy[j][0] or sorted_buy[j][1] == 0):
        j += 1
    if j < len(sorted_buy):
        # we have a trade
        amount = min(sorted_buy[j][1], sorted_sell[i][1])
        print(f"we have a trade {sorted_buy[j]} and {sorted_sell[i]} for {amount} amount \n")
        sorted_buy[j][1] -= amount
        sorted_sell[i][1] -= amount
    if not sorted_sell[i][1]:
        i += 1