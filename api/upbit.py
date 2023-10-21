import traceback
import pyupbit
import requests
from consts import *
import util
import asyncio
import websockets
import json
import socket
import uuid
import logging
import pandas as pd
from datetime import datetime

"""
Docs: https://pyupbit.readthedocs.io/en/latest/
"""
def get_all_ticker():
    """데이터 수신할 TICKER 목록(KRW, BTC마켓 합산)"""
    krw_ticker = pyupbit.get_tickers(fiat="KRW")
    btc_ticker = pyupbit.get_tickers(fiat="BTC")
    only_in_btc = [ticker for ticker in btc_ticker if "KRW-" + ticker.split("-")[1] not in krw_ticker]

    return krw_ticker + only_in_btc

def get_usd_price(exchange_price):
    """UPBIT 달러정보 조회"""
    data = requests.get('https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWUSD').json()
    exchange_price["USD"] = {'base': data[0]['basePrice']}
    logging.info('환율정보 조회 : [{}]'.format(exchange_price["USD"]))

async def connect_socket_spot_ticker(exchange_price):
    """UPBIT 소켓연결 후 실시간 가격 저장"""
    global exchange
    exchange = 'Upbit'

    logging.info(f"{exchange} connect_socket")
    while True:
        try:
            await util.send_to_telegram('[{}] Creating new connection...'.format(exchange))
            start_time = datetime.now()
            util.clear_exchange_price(exchange, exchange_price)

            logging.info(f"{exchange} WebSocket 연결 합니다. (Spot)")
            async with websockets.connect('wss://api.upbit.com/websocket/v1',
                                          ping_interval=None, ping_timeout=30, max_queue=10000) as websocket:
                logging.info(f"{exchange} WebSocket 연결 완료. (Spot)")

                subscribe_fmt = [
                    {'ticket': str(uuid.uuid4())[:6]},
                    {
                        'type': 'ticker',
                        'codes': get_all_ticker(),
                        'isOnlyRealtime': True
                    },
                ]
                subscribe_data = json.dumps(subscribe_fmt)

                logging.info(f"{exchange} Spot 데이터 요청 등록")
                await websocket.send(subscribe_data)

                logging.info(f"{exchange} 소켓 Spot 데이터 수신")
                while True:
                    try:
                        data = await asyncio.wait_for(websocket.recv(), 10)
                        data = json.loads(data)

                        if 'code' not in data: # 응답 데이터(딕셔너리)에 code가 없는 경우 제외
                            logging.info(f"{exchange} [Data error] : {data}")
                            continue
                        if "BTC" in exchange_price:
                            btc_price = float(exchange_price['BTC'][exchange])
                        else:
                            btc_price = 0

                        base_ticker = data['code'].split('-')[0] # KRW-BTC > KRW(기준통화)
                        ticker = data['code'].split('-')[1]     # KRW-BTC > BTC(시세조회대코인)

                        if base_ticker == "BTC":
                            continue

                        if ticker not in exchange_price:
                            exchange_price[ticker] = {}
                            for exchange_list in EXCHANGE_LIST:
                                exchange_price[ticker].update({exchange_list: None})
                        if base_ticker == "BTC":  # 기준통화가 BTC인 경우는 "현재 가격 x BTC가격 "이 원화환산 가격
                            exchange_price[ticker][exchange] = float(data['trade_price']) * btc_price
                        else:  # 기준통화가 원화인 경우, 현재가격(trade_price) 그대로 저장
                            exchange_price[ticker][exchange] = float(data['trade_price'])

                        if util.is_need_reset_socket(start_time):  # 매일 아침 9시 소켓 재연결
                            await util.send_to_telegram('[{}] Time to new connection...'.format(exchange))
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
                    except:
                        logging.info(traceback.format_exc())
                await websocket.close()
        except socket.gaierror:
            logging.info(f"{exchange} WebSocket 연결 실패 {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
            await asyncio.sleep(SOCKET_RETRY_TIME)
        except ConnectionRefusedError:
            logging.info(f"{exchange} WebSocket 연결 실패 {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
            await asyncio.sleep(SOCKET_RETRY_TIME)

async def connect_socket_spot_orderbook(exchange_price, exchange_price_orderbook):
    """UPBIT 소켓연결 후 실시간 가격 저장"""
    global exchange
    exchange = 'Upbit'
    await  asyncio.sleep(30)
    logging.info(f"{exchange} connect_socket_orderbook")
    # await asyncio.sleep(60)
    while True:
        try:
            await util.send_to_telegram('[{}] Creating new connection...'.format(exchange))
            start_time = datetime.now()
            # util.clear_exchange_price(exchange, exchange_price_orderbook)

            logging.info(f"{exchange} WebSocket 연결 합니다. (Orderbook)")
            async with (websockets.connect('wss://api.upbit.com/websocket/v1',
                                          ping_interval=None, ping_timeout=30, max_queue=10000) as websocket):
                logging.info(f"{exchange} WebSocket 연결 완료. (Orderbook)")

                subscribe_fmt = [
                    {'ticket': str(uuid.uuid4())[:6]},
                    {
                        'type': 'orderbook',
                        'codes': get_all_ticker(),
                        'isOnlyRealtime': True
                    },
                ]
                subscribe_data = json.dumps(subscribe_fmt)

                logging.info(f"{exchange} Orderbook 데이터 요청 등록")
                await websocket.send(subscribe_data)

                logging.info(f"{exchange} 소켓 Orderbook 데이터 수신")
                while True:
                    try:
                        data = await asyncio.wait_for(websocket.recv(), 10)
                        data = json.loads(data)

                        if 'code' not in data: # 응답 데이터(딕셔너리)에 code가 없는 경우 제외
                            logging.info(f"{exchange} [Data error] : {data}")
                            continue

                        if "BTC" in exchange_price:
                            btc_price = float(exchange_price['BTC'][exchange])
                        else:
                            btc_price = 0

                        base_ticker = data['code'].split('-')[0] # KRW-BTC > KRW(기준통화)
                        ticker = data['code'].split('-')[1]     # KRW-BTC > BTC(시세조회대코인)

                        orderbook_units_temp = []
                        orderbook_len = len(data['orderbook_units'])

                        for i in range(0,ORDERBOOK_SIZE):
                            orderbook_units_temp.append({"ask_price" : 0, "bid_price" : 0, "ask_size" : 0, "bid_size" : 0 })

                        if orderbook_len > ORDERBOOK_SIZE:
                            for i in range(0, ORDERBOOK_SIZE):
                                if base_ticker == "BTC":
                                    data['orderbook_units'][i]['ask_price'] = data['orderbook_units'][i]['ask_price'] * btc_price
                                    data['orderbook_units'][i]['bid_price'] = data['orderbook_units'][i]['bid_price'] * btc_price
                                    orderbook_units_temp[i] = data['orderbook_units'][i]
                                else:
                                    orderbook_units_temp[i] = data['orderbook_units'][i]
                        else:
                            for i in range(0, orderbook_len):
                                if base_ticker == "BTC":
                                    data['orderbook_units'][i]['ask_price'] = data['orderbook_units'][i]['ask_price'] * btc_price
                                    data['orderbook_units'][i]['bid_price'] = data['orderbook_units'][i]['bid_price'] * btc_price
                                    orderbook_units_temp[i] = data['orderbook_units'][i]
                                else:
                                    orderbook_units_temp[i] = data['orderbook_units'][i]

                        if ticker not in exchange_price_orderbook:
                            exchange_price_orderbook[ticker] = {}
                            for exchange_list in EXCHANGE_LIST:
                                exchange_price_orderbook[ticker].update({exchange_list: None})
                                exchange_price_orderbook[ticker][exchange_list] = {"orderbook_units": [None]}

                        # 호가 데이터 저장
                        exchange_price_orderbook[ticker][exchange]["orderbook_units"] = orderbook_units_temp


                        if util.is_need_reset_socket(start_time):  # 매일 아침 9시 소켓 재연결
                            await util.send_to_telegram('[{}] Time to new connection...'.format(exchange))
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
                    except:
                        logging.info(traceback.format_exc())
                await websocket.close()
        except socket.gaierror:
            logging.info(f"{exchange} WebSocket 연결 실패 {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
            await asyncio.sleep(SOCKET_RETRY_TIME)
        except ConnectionRefusedError:
            logging.info(f"{exchange} WebSocket 연결 실패 {SOCKET_RETRY_TIME}초 후 재연결 합니다.")
            await asyncio.sleep(SOCKET_RETRY_TIME)

async def get_exchange_accum_trade_price(exchange_accum_trade_price, exchange_price):
    """ Upbit 누적거래대금(단위금액:억) 조회 및 저장  """
    # exchange_price에 BTC가격이 없으면 pyupbit를 이용해 조회
    logging.info(f"{exchange} get_exchange_accum_trade_price")
    btc_price = pyupbit.get_current_price("KRW-BTC")
    for ticker in get_all_ticker():
        df = pyupbit.get_ohlcv(ticker, count=1)
        if isinstance(df, pd.DataFrame):
            currency = ticker.split("-")[0]
            symbol = ticker.split("-")[1]  # KRW-XRP > XRP
            if symbol not in exchange_accum_trade_price:
                exchange_accum_trade_price[symbol] = dict.fromkeys(EXCHANGE_LIST, None)
            if currency == 'BTC':  # BTC마켓 코인은 BTC가격을 곱해줌
                exchange_accum_trade_price[symbol][exchange] = round(df[-1:]['value'].values[0] * \
                                                                     btc_price / MILLION, 2)
            else:  # 원화마켓 코인은 그대로 저장
                exchange_accum_trade_price[symbol][exchange] = round(df[-1:]['value'].values[0] / MILLION, 2)
            # logging.info(f"{exchange} {ticker} 누적거래대금 : [{exchange_accum_trade_price}]")
        await asyncio.sleep(0.1) # pyupbit 안정적으로 호출하기 위해 sleep

if __name__ == "__main__":
    logging.info(get_usd_price())