import logging
import cloudscraper
from bs4 import BeautifulSoup

def get_currency_data(currency, exchange_rate):
    # 크롤링할 웹 페이지의 URL
    url = ''
    if currency == 'USD':
        url = 'https://kr.investing.com/currencies/usd-krw-historical-data'
    elif currency == 'JPY':
        url = 'https://kr.investing.com/currencies/jpy-krw-historical-data'

    scraper = cloudscraper.create_scraper()
    html = scraper.get(url).content

    soup = BeautifulSoup(html, 'html.parser')
    usd_price_class = soup.find(attrs={"data-test": "instrument-price-last"})

    #table = soup.select("text-5xl/9 font-bold md:text-[42px] md:leading-[60px] text-[#232526]")
    #print(f"TEST!!!\n {usd_price_class}")

    # 요소가 존재하는 경우 텍스트 내용 추출
    if usd_price_class:
        last_value = float(usd_price_class.text.strip().replace(',', ''))

        if currency == 'JPY':
            last_value = round(last_value * 100,2)
        exchange_rate[currency]['investing'] = last_value

    scraper.close()


