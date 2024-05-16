from bs4 import BeautifulSoup
import requests
resp = requests.get('https://oblenergo.cv.ua/shutdowns/')
soap = BeautifulSoup(resp.text, "html.parser")

data_div = soap.find('div', {"id": "gsv"}).find('div').find_all('div')
status_dict = {'мз': None, 'в': False, 'з': True}
hours = soap.find('div', {"id": "gsv"}).find('div').p.find_all('b')
hours_val = [val.next for val in hours[:-1]]
power_data = []
for datas in data_div:
    group_id = datas['data-id']
    power = [pow.text for pow in datas]
    power_data.append({"group_id": group_id, "data": [{"hour": v1, "status": status_dict.get(v2)} for v1, v2 in zip(hours_val, power)]})

print(power_data)
