import json

def crawl_then_hop(qty, start_price, indicator):
    increment = 0
    result = []
    total_qty = 0
    total_price = 0
    qty = qty
    start_price = start_price
    while True:
        ally_price = start_price + (increment * indicator)
        if total_qty + int(qty) > 1500:
            break
        ally_qty = int(qty)
        total_qty += ally_qty
        total_price += ally_price * ally_qty
        result.append((ally_price, ally_qty, total_price / total_qty))
        if total_qty < 600:
            incremental_tick = 200
            qty += 10
        else:
            incremental_tick = 400
            qty = min(300, qty * 1.5)
        increment += incremental_tick * 0.5

    return result

def marathon(qty, start_price, indicator):
    increment = 0
    result = []
    total_qty = 0
    total_price = 0
    start_price = start_price
    initial_qty = qty
    while True:
        if total_qty < 600:
            incremental_tick = 50
        else:
            incremental_tick = 600
            qty = max(initial_qty * 4, qty * 1.2)
        increment += incremental_tick * 0.5
        ally_price = start_price + (increment * indicator)
        if total_qty + int(qty) > 1800:
            break
        ally_qty = int(qty)
        total_qty += ally_qty
        total_price += ally_price * ally_qty
        result.append((ally_price, ally_qty))

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
            incremental_tick += 3
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

def bool_play(qty, start_price, indicator):
    # Ideal quantity value is 10
    increment = 0
    result = []
    total_qty = 0
    total_price = 0
    qty = qty
    start_price = start_price
    incremental_tick = 20
    bool_factor = 1
    while True:
        ally_price = start_price + (increment * indicator)
        if total_qty + int(qty) > 1500:
            break

        ally_qty = int(qty) * bool_factor
        total_qty += ally_qty
        total_price += ally_price * ally_qty
        result.append((ally_price, ally_qty, total_qty, total_price / total_qty))
        if total_qty < 500:
            incremental_tick += 3
            qty += 1
            if total_qty > 100:
                bool_factor = 2
        else:
            bool_factor = 1
            incremental_tick = 600
            qty = 150
        increment = increment + (incremental_tick * 0.5 * bool_factor)

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


def factor_ever_step(qty, start_price, indicator):
    increment = 0
    incremental_tick = 200
    qty = qty
    result = []
    total_qty = 0
    total_price = 0
    while True:
        if qty > 5000:
            break
        increment += incremental_tick * 0.5
        ally_price = start_price + increment
        ally_qty = int(qty)
        total_qty += ally_qty
        total_price += ally_price * ally_qty
        result.append((ally_price, ally_qty, total_qty, total_price / total_qty))
        qty *= 1.5

    return result


if __name__ == '__main__':
    r = marathon(30, 11000, 1)
    with open('2.txt', 'w') as f:
        f.write(json.dumps(r, indent=4))
