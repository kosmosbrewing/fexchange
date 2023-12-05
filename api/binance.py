import hashlib

import aiohttp
import ujson
import requests
from consts import *
import util
import asyncio
import websockets
import json
import socket
import logging
import os
import time
import hmac
from datetime import datetime
"""
Docs: https://binance-docs.github.io/apidocs/spot/en/
"""
def get_all_ticker():
    """데이터 수신할 SYMBOL 목록"""
    res = requests.get("https://api.binance.com/api/v3/exchangeInfo")
    res = res.json()
    return [s['symbol'].lower() + "@miniTicker" for s in res['symbols'] if "USDT" in s['symbol']]

def get_all_book_ticker():
    """데이터 수신할 SYMBOL 목록"""
    res = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo")
    res = res.json()

    return [s['symbol'].lower() + "@depth" for s in res['symbols'] if "USDT" in s['symbol']]

def get_binance_order_data(exchange_data):
    """데이터 수신할 SYMBOL 목록"""
    res = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo")
    res = res.json()

    for s in res['symbols']:
        if "USDT" in s['symbol']:
            ticker = s['symbol'].replace("USDT", "")
            exchange_data[ticker] = {
                'quantity_precision': s['quantityPrecision'],
                'min_notional': float(s['filters'][5]['notional'])
            }
    logging.info(f"Binance Quantity Precision 요청 : {exchange_data}")
    #print([s['symbol'].lower() + "|" + str(s['quantityPrecision']) for s in res['symbols'] if "USDT" in s['symbol']])

def get_min_notional(exchange_data):
    """데이터 수신할 SYMBOL 목록"""
    res = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo")
    res = res.json()

    for s in res['symbols']:
        if "USDT" in s['symbol']:
            ticker = s['symbol'].replace("USDT", "")
            print(f"{ticker} {s['filters'][5]['notional']}")

            exchange_data[ticker] = {'min_notional': s['quantityPrecision']}

    logging.info(f"Binance Quantity Precision 요청 : {exchange_data}")
    #print([s['symbol'].lower() + "|" + str(s['quantityPrecision']) for s in res['symbols'] if "USDT" in s['symbol']])



async def check_order(ticker, order_result, lock):
    access_key = os.environ['BINANCE_OPEN_API_ACCESS_KEY']
    secret_key = os.environ['BINANCE_OPEN_API_SECRET_KEY']
    server_url = 'https://fapi.binance.com/fapi/v1/order'
    timestamp = int(time.time() * 1000)

    # 주문 정보 (예시 값)
    payload = {
        'symbol': ticker,  # 거래 코인
        'orderId': order_result['orderId'],  # 주문 유형 (시장가, 지정가 등)
        'timestamp': timestamp
    }
    # 파라미터를 쿼리스트링 형태로 변환
    query_string = '&'.join(["{}={}".format(k, v) for k, v in payload.items()])
    # 헤더 설정
    headers = {
        'X-MBX-APIKEY': access_key
    }
    # 서명 생성
    signature = hmac.new(key=secret_key.encode('utf-8'), msg=query_string.encode('utf-8'),
                         digestmod=hashlib.sha256).hexdigest()
    payload = {
        'symbol': ticker,  # 거래 코인
        'orderId': order_result['orderId'],  # 주문 유형 (시장가, 지정가 등)
        'timestamp': timestamp,
        'signature': signature
    }
    # 서명을 요청 파라미터에 추가
    # server_url = f'{server_url}?{query_string}&signature={signature}'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(server_url, headers=headers, params=payload) as res:
                data = await res.json()

        async with lock:
            logging.info("BINANCE 주문 확인 결과")
            logging.info(f"BINANCE_REQUEST|{ticker}|orderId|{order_result['orderId']}")
            logging.info(f"BINANCE_RESPONSE|{data}")
            order_result['binance_price'] = float(data['avgPrice'])
            order_result['binance_quantity'] = float(data['executedQty'])
    except Exception as e:
        logging.info("BINANCE 주문 확인 실패")
        logging.info(f"Exception : {e}")

async def futures_order(ticker, side, quantity, order_result, lock):
    access_key = os.environ['BINANCE_OPEN_API_ACCESS_KEY']
    secret_key = os.environ['BINANCE_OPEN_API_SECRET_KEY']
    server_url = 'https://fapi.binance.com/fapi/v1/order'
    timestamp = int(time.time() * 1000)

    if side == 'ask':
        side = 'SELL'
    elif side == 'bid':
        side = 'BUY'

    # 주문 정보 (예시 값)
    payload = {
        'symbol': ticker,  # 거래 코인
        'side': side,  # 매수 또는 매도
        'type': 'MARKET',  # 주문 유형 (시장가, 지정가 등)
        'quantity': quantity,  # 주문 수량
        'timestamp': timestamp
    }
    # 파라미터를 쿼리스트링 형태로 변환
    query_string = '&'.join(["{}={}".format(k, v) for k, v in payload.items()])
    # 헤더 설정
    headers = {
        'X-MBX-APIKEY': access_key
    }
    # 서명 생성
    signature = hmac.new(key=secret_key.encode('utf-8'), msg=query_string.encode('utf-8'),
                         digestmod=hashlib.sha256).hexdigest()
    # 서명을 요청 파라미터에 추가
    server_url = f'{server_url}?{query_string}&signature={signature}'

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(server_url, headers=headers) as res:
                data = await res.json()

        #res = requests.post(server_url, headers=headers)
        #data = res.json()

        async with lock:
            logging.info("BINANCE 주문 결과")
            logging.info(f"BINANCE_REQUEST|{ticker}|SIDE|{side}|QUANTITY|{quantity}")
            logging.info(f"BINANCE_RESPONSE|{data}")
            order_result['orderId'] = data['orderId']
    except Exception as e:
        logging.info("BINANCE 주문 실패")
        logging.info(f"Exception : {e}")
async def futures_order_all(ticker, side):
    access_key = os.environ['BINANCE_OPEN_API_ACCESS_KEY']
    secret_key = os.environ['BINANCE_OPEN_API_SECRET_KEY']
    server_url = 'https://fapi.binance.com/fapi/v1/order'
    timestamp = int(time.time() * 1000)

    if side == 'ask':
        side = 'BUY'
    else:
        side = 'SELL'

    # 주문 정보 (예시 값)
    payload = {
        'symbol': ticker,  # 거래 코인
        'side': side,  # 매수 또는 매도
        'type': 'MARKET',  # 주문 유형 (시장가, 지정가 등)
        'closePosition': True,  # 주문 수량
        'timestamp': timestamp
    }
    # 파라미터를 쿼리스트링 형태로 변환
    query_string = '&'.join(["{}={}".format(k, v) for k, v in payload.items()])

    # 헤더 설정
    headers = {
        'X-MBX-APIKEY': access_key
    }

    # 서명 생성
    signature = hmac.new(key=secret_key.encode('utf-8'), msg=query_string.encode('utf-8'),
                         digestmod=hashlib.sha256).hexdigest()

    logging.info(f"BINANCE_ORDER|{ticker}|SIDE|{side}|QUANTITY|ALL")
    # 서명을 요청 파라미터에 추가
    server_url = f'{server_url}?{query_string}&signature={signature}'

    res = requests.post(server_url, headers=headers)
    logging.info(f"BINANCE_RESPONSE|{res.json()}")
async def connect_socket_futures_orderbook(exchange_data, orderbook_info, socket_connect):
    """Binance 소켓연결"""
    exchange = BINANCE
    await asyncio.sleep(SOCKET_ORDERBOOK_DELAY)
    logging.info(f"{exchange} connect_socket")
    while True:
        try:
            #await util.send_to_telegram('[{}] Creating new connection...'.format(exchange))
            start_time = datetime.now()

            logging.info(f"{exchange} WebSocket 연결 합니다. (Orderbook)")
            async with (websockets.connect('wss://fstream.binance.com/ws', ping_interval=SOCKET_PING_INTERVAL,
                                          ping_timeout=SOCKET_PING_TIMEOUT, max_queue=10000) as websocket):
                socket_connect[1] = 1
                logging.info(f"{exchange} WebSocket 연결 완료. (Orderbook) | Socket Connect: {socket_connect[1]}")

                params_ticker = []
                tickers = get_all_book_ticker()
                for idx, ticker in enumerate(tickers):
                    params_ticker.append(ticker)

                    if len(params_ticker) > 50 or idx == len(tickers)-1:
                        subscribe_fmt = {
                            "method": "SUBSCRIBE",
                            "params": params_ticker,
                            "id": 1
                        }

                        subscribe_data = json.dumps(subscribe_fmt)

                        logging.info(f"{exchange} Orderbook 데이터 요청 등록")
                        await websocket.send(subscribe_data)
                        await asyncio.sleep(1)
                        params_ticker = []

                logging.info(f"{exchange} 소켓 Orderbook 데이터 수신")
                while True:
                    try:
                        data = await asyncio.wait_for(websocket.recv(), 10)
                        data = ujson.loads(data)

                        ticker = data['s'].replace("USDT", "") if 's' in data else None

                        if not ticker:  # ticker가 없는 데이터의 경우 저장 불가
                            continue

                        '''
                        if 'USD' in exchange_data:
                            usd_price = exchange_data['USD']['base']
                        else:
                            usd_price = 0
                        '''

                        ask_len = len(data['a'])
                        bid_len = len(data['b'])

                        if ticker not in orderbook_info:
                            orderbook_info[ticker] = {}
                            for exchange_list in EXCHANGE_LIST:
                                orderbook_info[ticker].update({exchange_list: None})
                                orderbook_info[ticker][exchange_list] = {"orderbook_units": []}

                                for i in range(0, ORDERBOOK_SIZE):
                                    orderbook_info[ticker][exchange_list]["orderbook_units"].append({"ask_price": 0, "bid_price": 0, "ask_size": 0, "bid_size": 0})

                        if ask_len > ORDERBOOK_SIZE:
                            for i in range(0, ORDERBOOK_SIZE):
                                orderbook_info[ticker][exchange]["orderbook_units"][i]['ask_price'] = float(data['a'][i][0]) * TETHER
                                orderbook_info[ticker][exchange]["orderbook_units"][i]['ask_size'] = data['a'][i][1]
                        else:
                            for i in range(0, ask_len):
                                orderbook_info[ticker][exchange]["orderbook_units"][i]['ask_price'] = float(data['a'][i][0]) * TETHER
                                orderbook_info[ticker][exchange]["orderbook_units"][i]['ask_size'] = data['a'][i][1]
                        j = 0
                        if bid_len > ORDERBOOK_SIZE:
                            for i in range(bid_len-1, bid_len-1-ORDERBOOK_SIZE, -1):
                                orderbook_info[ticker][exchange]["orderbook_units"][j]['bid_price'] = float(data['b'][i][0]) * TETHER
                                orderbook_info[ticker][exchange]["orderbook_units"][j]['bid_size'] = data['b'][i][1]
                                j += 1
                        else:
                            for i in range(bid_len-1, -1, -1):
                                orderbook_info[ticker][exchange]["orderbook_units"][j]['bid_price'] = float(data['b'][i][0]) * TETHER
                                orderbook_info[ticker][exchange]["orderbook_units"][j]['bid_size'] = data['b'][i][1]
                                j += 1

                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                        try:
                            logging.info(f"{exchange} WebSocket 데이터 수신 Timeout {SOCKET_PING_TIMEOUT}초 후 재연결 합니다.")
                            pong = await websocket.ping()
                            await asyncio.wait_for(pong, timeout=SOCKET_PING_TIMEOUT)
                        except:
                            logging.info(f"{exchange} WebSocket Polling Timeout {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
                            await asyncio.sleep(SOCKET_RETRY_TIME)
                            break
                socket_connect[1] = 0
                logging.info(f"{exchange} WebSocket 연결 종료. (Orderbook 초기화) | Socket Connect: {socket_connect[1]}")
                await websocket.close()
        except socket.gaierror:
            logging.info(f"{exchange} WebSocket 연결 실패 {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
            await asyncio.sleep(SOCKET_RETRY_TIME)
            continue
        except ConnectionRefusedError:
            logging.info(f"{exchange} WebSocket 연결 실패 {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
            await asyncio.sleep(SOCKET_RETRY_TIME)
            continue

async def connect_socket_spot_ticker(exchange_data):
    """Binance 소켓연결"""
    exchange = BINANCE

    logging.info(f"{exchange} connect_socket")
    while True:
        try:
            #await util.send_to_telegram('[{}] Creating new connection...'.format(exchange))
            start_time = datetime.now()
            util.clear_exchange_data(exchange, exchange_data)

            logging.info(f"{exchange} WebSocket 연결 합니다.")
            async with websockets.connect('wss://stream.binance.com:9443/ws', ping_interval=SOCKET_PING_INTERVAL,
                                          ping_timeout=SOCKET_PING_TIMEOUT, max_queue=10000) as websocket:
                logging.info(f"{exchange} WebSocket 연결 완료.")

                params_ticker = []
                tickers = get_all_ticker()
                for idx, ticker in enumerate(tickers):
                    params_ticker.append(ticker)

                    if len(params_ticker) > 50 or idx == len(tickers)-1:
                        subscribe_fmt = {
                            "method": "SUBSCRIBE",
                            "params": params_ticker,
                            "id": 1
                        }

                        subscribe_data = json.dumps(subscribe_fmt)

                        logging.info(f"{exchange} 데이터 요청 등록")
                        await websocket.send(subscribe_data)
                        await asyncio.sleep(1)
                        params_ticker = []

                logging.info(f"{exchange} 소켓 데이터 수신")
                while True:
                    try:
                        data = await asyncio.wait_for(websocket.recv(), 10)
                        data = json.loads(data)

                        ticker = data['s'].replace("USDT", "") if 's' in data else None
                        if not ticker:  # ticker가 없는 데이터의 경우 저장 불가
                            continue
                        if ticker not in exchange_data:
                            exchange_data[ticker] = {exchange: None}

                        exchange_data[ticker][exchange] = float(data['c']) * \
                                        exchange_data['USD']['base'] if 'USD' in exchange_data else 0

                        if util.is_need_reset_socket(start_time):  # 매일 아침 9시 소켓 재연결
                            #await util.send_to_telegram('[{}] Time to new connection...'.format(exchange))
                            break

                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                        try:
                            logging.info(f"{exchange} WebSocket 데이터 수신 Timeout {SOCKET_PING_TIMEOUT}초 후 재연결 합니다.")
                            pong = await websocket.ping()
                            await asyncio.wait_for(pong, timeout=SOCKET_PING_TIMEOUT)
                        except:
                            logging.info(f"{exchange} WebSocket Polling Timeout {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
                            await asyncio.sleep(SOCKET_RETRY_TIME)
                            break
                await websocket.close()
        except socket.gaierror:
            logging.info(f"{exchange} WebSocket 연결 실패 {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
            await asyncio.sleep(SOCKET_RETRY_TIME)
            continue
        except ConnectionRefusedError:
            logging.info(f"{exchange} WebSocket 연결 실패 {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
            await asyncio.sleep(SOCKET_RETRY_TIME)
            continue


async def connect_socket_futures_ticker(exchange_data):
    """Binance 소켓연결"""
    exchange = BINANCE
    logging.info(f"{exchange} connect_socket")
    while True:
        try:
            #await util.send_to_telegram('[{}] Creating new connection...'.format(exchange))
            start_time = datetime.now()
            util.clear_exchange_data(exchange, exchange_data)

            logging.info(f"{exchange} WebSocket 연결 합니다. (Spot)")
            async with websockets.connect('wss://fstream.binance.com/ws', ping_interval=SOCKET_PING_INTERVAL,
                                          ping_timeout=SOCKET_PING_TIMEOUT, max_queue=10000) as websocket:
                logging.info(f"{exchange} WebSocket 연결 완료. (Spot)")

                params_ticker = []
                tickers = get_all_ticker()
                for idx, ticker in enumerate(tickers):
                    params_ticker.append(ticker)

                    if len(params_ticker) > 50 or idx == len(tickers)-1:
                        subscribe_fmt = {
                            "method": "SUBSCRIBE",
                            "params": params_ticker,
                            "id": 1
                        }

                        subscribe_data = json.dumps(subscribe_fmt)

                        logging.info(f"{exchange} Futures 데이터 요청 등록")
                        await websocket.send(subscribe_data)
                        await asyncio.sleep(1)
                        params_ticker = []

                logging.info(f"{exchange} 소켓 Futures 데이터 수신")
                while True:
                    try:
                        data = await asyncio.wait_for(websocket.recv(), 10)
                        data = json.loads(data)

                        ticker = data['s'].replace("USDT", "") if 's' in data else None

                        if not ticker:  # ticker가 없는 데이터의 경우 저장 불가
                            continue
                        if ticker not in exchange_data:
                            exchange_data[ticker] = {}
                            for exchange_list in EXCHANGE_LIST:
                                exchange_data[ticker].update({exchange_list: None})

                        if 'USD' in exchange_data:
                            usd_price = exchange_data['USD']['base']
                        else:
                            usd_price = 0

                        exchange_data[ticker][exchange] = float(data['c']) * usd_price

                        if util.is_need_reset_socket(start_time):  # 매일 아침 9시 소켓 재연결
                            logging.info('[{}] Time to new connection...'.format(exchange))
                            #await util.send_to_telegram('[{}] Time to new connection...'.format(exchange))
                            break

                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                        try:
                            logging.info(f"{exchange} WebSocket 데이터 수신 Timeout {SOCKET_PING_TIMEOUT}초 후 재연결 합니다.")
                            pong = await websocket.ping()
                            await asyncio.wait_for(pong, timeout=SOCKET_PING_TIMEOUT)
                        except:
                            logging.info(f"{exchange} WebSocket Polling Timeout {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
                            await asyncio.sleep(SOCKET_RETRY_TIME)
                            break
                await websocket.close()
        except socket.gaierror:
            logging.info(f"{exchange} WebSocket 연결 실패 {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
            await asyncio.sleep(SOCKET_RETRY_TIME)
            continue
        except ConnectionRefusedError:
            logging.info(f"{exchange} WebSocket 연결 실패 {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
            await asyncio.sleep(SOCKET_RETRY_TIME)
            continue
def change_leverage_all_ticker():
    # 개발자가 Binance에서 발급받은 API 키와 시크릿 키
    access_key = os.environ['BINANCE_OPEN_API_ACCESS_KEY']
    secret_key = os.environ['BINANCE_OPEN_API_SECRET_KEY']
    server_url = 'https://fapi.binance.com/fapi/v1/marginType'

    # 변경할 레버리지
    new_leverage = 'ISOLATED'

    # 요청 헤더
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-MBX-APIKEY': access_key
    }
    # 모든 티커 가져오기
    exchange_info_url = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
    exchange_info_response = requests.get(exchange_info_url)
    symbols = exchange_info_response.json()['symbols']
    # 각 티커에 대해 레버리지 설정 변경
    for symbol_info in symbols:
        symbol = symbol_info['symbol']
        timestamp = int(time.time() * 1000)
        # 요청 매개변수
        params = {
            'symbol': symbol,
            'marginType': new_leverage,
            'timestamp': timestamp
        }
        # 시그니처 생성
        query_string = '&'.join([f'{key}={params[key]}' for key in params])
        signature = hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        # API 요청 보내기
        response = requests.post(server_url, params={**params, 'signature': signature}, headers=headers)
        data = response.json()
        # 응답 출력
        print(f"Symbol: {symbol}, Leverage: {new_leverage}, Response: {data}")
        time.sleep(0.1)  # Binance API 규칙을 준수하기 위해 각 요청 사이에 일정한 시

if __name__ == "__main__":
    get_binance_order_data({})
    #change_leverage_all_ticker()

    #exchange_data = {}
    #get_quantity_precision(exchange_data)
    #futures_order('ORDI', 'ask', '10000', '2')
