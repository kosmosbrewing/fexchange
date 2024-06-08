import logging
import requests

def get_currency_data(currency, exchange_rate):
    # 크롤링할 웹 페이지의 URL
    # 환율 정보 가져오기
    url = 'https://api.tossbank.com/api-public/fx/v1/exchange-rates'
    response = requests.get(url)

    # 요청이 성공했는지 확인
    if response.status_code == 200:
        data = response.json()
        for detail in data['exchangeRates']:
            #print(detail)
            if detail['base']['currency'] == currency:
                last_value = float(detail['exchangeRate'])
                #print(f"{currency} {detail['exchangeRate']}")

                exchange_rate[currency]['toss'] = last_value

    else:
        print('페이지를 가져오는 데 문제가 발생했습니다. 상태 코드:', response.status_code)

    response.close()


if __name__ == "__main__":
    exchange_rate = {'USD': {}, 'JPY': {}}
    get_currency_data('USD', exchange_rate)

