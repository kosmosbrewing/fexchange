import asyncio
import util
import traceback
import logging
from consts import *
from crawl import hana, inveseting, toss

class Fexchange:
    def __init__(self):
        self.exchange_rate = {'USD': {}, 'JPY': {}}  # 거래소별 가격 데이터를 저장할 딕셔너리
        util.setup_logging()

    async def run(self):
        await util.send_to_telegram('🚀 Start Fexchange Bot 🚀')

        await asyncio.wait([
            asyncio.create_task(self.get_exchange_rate()),
            asyncio.create_task(self.get_exchange_rate_collect())
        ])

    async def get_exchange_rate(self):
        logging.info(f"환율 정보 조회 시작!")

        currency_list = ['USD', 'JPY']
        while True:
            try:
                for currency in currency_list:
                    hana.get_currency_data(currency, self.exchange_rate)
                    inveseting.get_currency_data(currency, self.exchange_rate)
                    #toss.get_currency_data(currency, self.exchange_rate)

                message = (f"🇺🇸 달러 현재 환율\n"
                           f"하나은행 : {self.exchange_rate['USD']['hana']:,}원\n"
                           #f"토스뱅크 : {self.exchange_rate['USD']['toss']:,}원\n"
                           f"인베스팅 : {self.exchange_rate['USD']['investing']:,}원\n")
                message += (f"🇯🇵 엔화 현재 환율\n"
                           f"하나은행 : {self.exchange_rate['JPY']['hana']:,}원\n"
                           #f"토스뱅크 : {self.exchange_rate['JPY']['toss']:,}원\n"
                           f"인베스팅 : {self.exchange_rate['JPY']['investing']:,}원")

                await util.send_to_telegram(message)

                await asyncio.sleep(10800)
            except Exception as e:
                logging.info(traceback.format_exc())

    async def get_exchange_rate_collect(self):
        logging.info(f"환율 정보 조회(데이터 수집) 시작!")

        currency_list = ['USD', 'JPY']
        while True:
            try:
                for currency in currency_list:
                    hana.get_currency_data(currency, self.exchange_rate)
                    inveseting.get_currency_data(currency, self.exchange_rate)
                    toss.get_currency_data(currency, self.exchange_rate)

                    message = (f"EXCHANGE_RATE[{currency}]|"
                               f"하나|{self.exchange_rate[currency]['hana']}|"
                               #f"토스|{self.exchange_rate[currency]['toss']}|"
                               f"인베스팅|{self.exchange_rate[currency]['investing']}")
                    
                    logging.info(message)
                await asyncio.sleep(3600)
            except Exception as e:
                logging.info(traceback.format_exc())

if __name__ == "__main__":
    fexchange = Fexchange()
    asyncio.run(fexchange.run())






