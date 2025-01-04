from bs4 import BeautifulSoup
from Logger import logger
# import requests
#
# resp = requests.get('https://oblenergo.cv.ua/shutdowns/')


def data_parser(data: str) -> dict | None:
    try:
        soap = BeautifulSoup(data, "html.parser")
        actual_date = soap.find('div', {'id': 'gsv_t'}).find('b').text
        next_day = soap.find('div', {'id': 'gsv_t'}).find('a')
        actual_time = soap.find('div', {'id': 'gsv_a'}).find('b').text
        data_div = soap.find('div', {"id": "gsv"}).find('div').find_all('div')
        status_dict = {'мз': None, 'в': False, 'з': True}
        hours = soap.find('div', {"id": "gsv"}).find('div').p.find_all('b')
        hours_val = [val.next for val in hours[:-1]]
        power_data = {}
        for datas in data_div:
            group_id = datas['data-id']
            power = [pow.text for pow in datas]
            group_data = {group_id: {v1: status_dict.get(v2) for v1, v2 in zip(hours_val, power)}}
            power_data.update(group_data)
        return {"data": power_data,
                "actual_date": actual_date,
                "actual_time": actual_time,
                "actual": f"{actual_date} {actual_time}",
                "next_day": next_day.text if next_day else next_day}
    except Exception as e:
        logger.exception(e)
        return None

#
# print(data_parser(resp.text))


