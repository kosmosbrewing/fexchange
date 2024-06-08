from datetime import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup


def get_usd():
    # 크롤링할 웹 페이지의 URL

    url = 'https://bank.shinhan.com/index.jsp#020501010100'

    today_date = datetime.today().strftime('%Y%m%d')
    today_string = datetime.today().strftime('%Y-%m-%d')
    curCd = 'USD'
    headers = {
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Origin': 'https://www.kebhana.com',
        'Host': 'www.kebhana.com',
        'Referer': 'https://www.kebhana.com/cms/rate/index.do?contentUrl=/cms/rate/wpfxd651_01i.do'}

    data = f'ajax=true&curCd={curCd}&inqStrDt={today_date}&pbldDvCd=3&requestTarget=searchContentDiv'
    #response = requests.post(url=url5, headers=headers, data=data, allow_redirects=True)

    # HTTP GET 요청을 보냄
    response = requests.post(url)

    # 요청이 성공했는지 확인
    if response.status_code == 200:

        soup = BeautifulSoup(response.text, 'html.parser')

        print(soup)
        '''
        ## 2단계 pd.read_html를 통해서 특정 테이블을 df로 바로 가져오기
        df = pd.read_html(response.text)[0]

        df.columns = ['회차', '시간', '현찰_살때', '현찰_팔때', '송금_보낼때', '송금_받을때', 'T/C', '외화', '매매기준율', '직전대비', '환가료율', '미화환산율']
        df = df[['회차', '시간', '매매기준율']]

        first_value = df.loc[df['회차'] == 1, '매매기준율'].values[0]
        second_value = df.loc[df['회차'] == 2, '매매기준율'].values[0]
        last_value = df.loc[df['회차'] == df['회차'].max(), '매매기준율'].values[0]
        last_num = df['회차'].max()
        mylist = [first_value, second_value, last_value]

        mymessage = f"기준일 : {today_string} 외화 : USD \n {mylist[0]} (1회) \n {mylist[1]} (2회) \n {mylist[2]} ({last_num}회, 최종)"

        print(mylist)'''
    else:
        print('페이지를 가져오는 데 문제가 발생했습니다. 상태 코드:', response.status_code)


    """데이터 수신할 SYMBOL 목록"""



if __name__ == "__main__":
    get_usd()

