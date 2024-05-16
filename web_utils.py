from bs4 import BeautifulSoup
import requests

# resp = requests.get('')


def data_parser(data: str):
    soap = BeautifulSoup(data, "html.parser")
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
    return {"data": power_data}
