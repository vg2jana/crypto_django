def f13800_12800():
    increment = 0
    result = []
    total_qty = 0
    total_price = 0
    qty = 30
    while True:
        if total_qty < 600:
            incremental_tick = 200
            qty += 10
        else:
            incremental_tick = 400
            qty = min(300, qty * 1.5)
        increment += incremental_tick * 0.5
        ally_price = 11000 + increment
        if total_qty + int(qty) > 2600:
            break
        ally_qty = int(qty)
        total_qty += ally_qty
        total_price += ally_price * ally_qty
        result.append((ally_price, ally_qty, total_price / total_qty))

    return result


def initial_plus1_later_200(qty, start_price, indicator):
    # Ideal quantity value is 10
    increment = 0
    result = []
    total_qty = 0
    total_price = 0
    qty = qty
    start_price = start_price
    incremental_tick = 20
    while True:
        if total_qty < 500:
            incremental_tick += 2
            qty += 1
        else:
            incremental_tick = 600
            qty = 150
        increment += incremental_tick * 0.5
        ally_price = start_price + (increment * indicator)
        if total_qty + int(qty) > 1500:
            break
        ally_qty = int(qty)
        total_qty += ally_qty
        total_price += ally_price * ally_qty
        result.append((ally_price, ally_qty))

    return result


def fIplus1_end():
    increment = 0
    result = []
    total_qty = 0
    total_price = 0
    qty = 5
    incremental_tick = 20
    while True:
        qty += 1
        increment += incremental_tick * 0.5
        ally_price = 11000 + increment
        if total_qty + int(qty) > 2600:
            break
        ally_qty = int(qty)
        total_qty += ally_qty
        total_price += ally_price * ally_qty
        result.append((ally_price, ally_qty, total_price / total_qty))

    return result


def fun_2():
    increment = 0
    incremental_tick = 20
    qty = 5
    result = []
    total_qty = 0
    total_price = 0
    while True:
        increment += incremental_tick * 0.5
        ally_price = 11000 + increment
        if ally_price < 0 or ally_price > 13000:
            break
        ally_qty = int(qty)
        total_qty += ally_qty
        total_price += ally_price * ally_qty
        result.append((ally_price, ally_qty, total_price / total_qty))
        qty *= 1.2
        incremental_tick += 5

    return result


if __name__ == '__main__':
    initial_plus1_later_200(5, 11401, 1)