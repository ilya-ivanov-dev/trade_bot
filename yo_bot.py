import json
import os
import requests
import time, datetime
import urllib, http.client
import hmac, hashlib
from settings import API_KEY, API_SECRET

# import matplotlib.pyplot as plt

""" КОММЕНТАРИЙ, ПОЯСНЯЮЩИЙ ТЕКСТ ПРОГРАММЫ

    Представленный код торгового бота можно рассматривать в качестве примера, КАК НЕ НУЖНО ПИСАТЬ КОД. 
    
    Это первая прикладная программа (04.2020), написанная в сжатые сроки, но выполнившая свою задачу.
    Рефакторинг не проводился, т.к. задача потеряла свою актуальность.
    
    Данный код нечитабелен, сложен в обслуживании и внесении изменений.     
    
    ДЛЯ УСРАНЕНИЯ УКАЗАННЫХ НЕДОСТАТКОВ ТРЕБУЕТСЯ РЕФАКТОРИНГ:
    1. Создание функции запуска бота, в которой запускается цикл while.
    2. Все функции выносятся из цикла. В цикле выполняется только вызов функций в необходимой последовательности.
    
"""




pump_value = 5  # сумма, на которую выполняется памп в BTC
max_volume = []  # список максимумов торговых пар
pairs = ['yo_btc']      # [ 'air_btc', 'frog_btc', 'tpt_btc', 'sex_btc', 'nax_btc']
cryptos = ['yo']              # [ 'air', 'frog', 'tpt', 'sex', 'nax']
funds = ['yo']                # [ 'air', 'frog', 'tpt', 'sex', 'nax']




while True:

    # t = datetime.datetime.now()
    string_pairs = '-'.join(pairs)
    res = requests.get(f'https://yobit.net/api/3/depth/{string_pairs}?limit=2000')
    res_obj = json.loads(res.text)
    res_obj.get('')
    # print(datetime.datetime.now() - t)

    ######################################################################################

    # Каждый новый запрос к серверу должен содержать увеличенное число в диапазоне 1-2147483646
    # Поэтому храним число в файле поблизости, каждый раз обновляя его
    nonce_file = "./nonce"
    if not os.path.exists(nonce_file):
        with open(nonce_file, "w") as out:
            out.write('1')

    # Будем перехватывать все сообщения об ошибках с биржи
    class YobitException(Exception):
        pass


    def call_api(**kwargs):
        # При каждом обращении к торговому API увеличиваем счетчик nonce на единицу
        with open(nonce_file, 'r+') as inp:
            nonce = int(inp.read())
            inp.seek(0)
            inp.write(str(nonce + 1))
            inp.truncate()

        payload = {'nonce': nonce}

        if kwargs:
            payload.update(kwargs)
        payload = urllib.parse.urlencode(payload)

        H = hmac.new(key=API_SECRET, digestmod=hashlib.sha512)
        H.update(payload.encode('utf-8'))
        sign = H.hexdigest()

        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Key": API_KEY,
                   "Sign": sign}
        conn = http.client.HTTPSConnection("yobitex.net", timeout=60)
        conn.request("POST", "/tapi/", payload, headers)
        response = conn.getresponse().read()

        conn.close()


        try:
            obj = json.loads(response.decode('utf-8'))

            if 'error' in obj and obj['error']:
                raise YobitException(obj['error'])
            return obj
        except json.decoder.JSONDecodeError:
            raise YobitException('Ошибка анализа возвращаемых данных, получена строка', response)


    def order_do(pair, rate, amount):  # создание ордера на продажу
        order = call_api(method="Trade", pair=pair, type='sell', rate=rate, amount=amount)
        return order


    def order_cancel(order_id):  # отмена ордера
        order = call_api(method="CancelOrder", order_id=order_id)
        return order


    def order_list(pair):  # список id открытых ордеров
        # получение списка открытых ордеров по каждой торговой паре
        info_active_orders = call_api(method="ActiveOrders", pair=pair)
        print(info_active_orders)

        active_order_id_list = []
        # order_rate_max = []
        # проверка наличия открытых ордеров текущей торговой пары
        if len(info_active_orders) > 1:
            active_order = info_active_orders['return']
            for key, val in active_order.items():
                active_order_id_list.append(key)
                # order_rate_max.append(val.get('rate'))

        print(f'Список открытых ордеров по паре {pair}: {active_order_id_list}')
        return active_order_id_list



    print('Получаем информацию по аккаунту', '*' * 30)
    # print(call_api(method="getInfo"))
    info_acc = call_api(method="getInfo")['return']['funds_incl_orders']
    # print(info_acc)

    # try:
    #     print('Создаем ордер на покупку', '*' * 30)
    #     print(call_api(method="Trade", pair="ltc_btc", type="buy", rate="0.1", amount=0.01))
    # except YobitException as e:
    #     print("Облом:", e)

    #############################################################################################


    num_crypto = 0
    funds = []
    for crypto in cryptos:      # получаем балансы по каждой монете из списка
        funds.append(info_acc[crypto])

    print(f'Балансы: {funds}')


    num_pair = 0
    pair_prices = []
    for pair in pairs:                              # перебираем торговые пары из заданного списка
        orders = res_obj.get(pair).get('asks')

        time.sleep(2)
        print(f'************* Информация по торговой паре {pair} *************')

        # print(f'Список id открытых ордеров: {order_list(pair)}')

        pair_sum = 0
        num_order = 0
        while pair_sum < pump_value and num_order < 1999:     # выборка ордеров из стакана на сумму до 5 BTC
            pair_price = orders[num_order][0]
            pair_count = orders[num_order][1]
            pair_sum += pair_price * pair_count
            num_order += 1

        # определение цен для выставления ордеров относительно максимума
        price_80 = format(pair_price * 0.80, '.8f')
        price_85 = format(pair_price * 0.85, '.8f')
        price_90 = format(pair_price * 0.90, '.8f')
        price_95 = format(pair_price * 0.95, '.8f')
        # pair_prices.append([price_80, price_85, price_90, price_95])

        print(f'Цены для выставления ордеров при макс цене {pair_price}')
        print(f'{price_80}\t {price_85}\t {price_90}\t {price_95}')

        # max_volume.append([pair, pair_sum -])
        # print(max_volume[num_pair])



        # отмена открытых ордеров
        print('Отменяем ордера ')
        for order in order_list(pair):
            order_cancel(order)
        print('Ордера отменены')
        # print(f'Список id открытых ордеров: {order_list(pair)}')

        # создание ордеров
        pair_max_val_btc = funds[num_pair] * pair_price

        print(f'Общий баланс монет: {funds[num_pair]}. Эквивалент в BTC: {pair_max_val_btc}')

        print('Создаем ордера')
        if pair_max_val_btc >= 0.0005:
            pair_amount_025 = format(funds[num_pair] * 0.25, '.8f')
            pair_amount_end = funds[num_pair] - float(pair_amount_025) * 3
            vol_btc = float(pair_amount_025) * float(price_80)
            print(f'Сумма BTC в ставке 0,8 : {price_80} * {pair_amount_025} = {vol_btc}  amount_end = {pair_amount_end}')
            order_do(pair, price_80, pair_amount_025)
            order_do(pair, price_85, pair_amount_025)
            order_do(pair, price_90, pair_amount_025)
            order_do(pair, price_95, pair_amount_end)
        elif pair_max_val_btc >= 0.00036:
            pair_amount_033 = format(funds[num_pair] * 0.33, '.8f')
            pair_amount_end = funds[num_pair] - funds[num_pair] * 0.66
            vol_btc = float(pair_amount_033) * float(price_85)
            print(f'Сумма BTC в ставке 0,85 : {price_85} * {pair_amount_033} = {vol_btc}')
            order_do(pair, price_85, pair_amount_033)
            order_do(pair, price_90, pair_amount_033)
            order_do(pair, price_95, pair_amount_end)
        elif pair_max_val_btc >= 0.00023:
            pair_amount_05 = format(funds[num_pair] * 0.5, '.8f')
            pair_amount_end = funds[num_pair] - funds[num_pair] * 0.5
            vol_btc = float(pair_amount_05) * float(price_90)
            print(f'Сумма BTC в ставке 0,9 : {price_90} * {pair_amount_05} = {vol_btc}')
            order_do(pair, price_90, pair_amount_05)
            order_do(pair, price_95, pair_amount_end)
        elif pair_max_val_btc >= 0.0001001:
            print(f'Сумма BTC в ставке 0,95 : {price_95} * {funds[num_pair]} = {vol_btc}')
            order_do(pair, price_95, funds[num_pair])

        print(f'Список id открытых ордеров: {order_list(pair)}')
        print()

        num_pair += 1

    time.sleep(60)
    print('')





