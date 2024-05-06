import requests
from datetime import datetime
import json
from Odoo import *

erp_url = 'https://erp.aimdynamics.com'
odoo_key = 'LPONkmPNibeba413OvxfiOyFFjVpzyMd'
odoo_secret = 'x9pPnEb02uc2dju83xaeQbrqTV3CTc3a'
odoo = Odoo(odoo_key, odoo_secret, erp_url)

shipstation_key = 'e081490e668640a58cacb1a061d33373'
shipstation_secret = '64ae04ab98a3485fa45c86b184c58679'

shipstation_write_to = 'product_data/shipstation.csv'
odoo_write_to = 'product_data/odoo.csv'

delimiter = '\t'

def get_date():
    current_datetime = datetime.now()
    return current_datetime.strftime("%Y-%m-%d %H:%M:%S")

#shipstation
def write_to_shipstation():
    page = 1
    all_products = []
    while True:
        url = 'https://ssapi.shipstation.com/products?pageSize=500&page=' + str(page)
        r = requests.get(url, auth=(shipstation_key, shipstation_secret),
                headers={'Accept':'application/json',"Content-Type":"application/json" })
        
        product_list = json.loads(r.text)['products']

        for product in product_list:
            #check to make sure warehouse location exists
            warehouse_location = product['warehouseLocation']
            if not warehouse_location:
                continue
            name = product['sku'].strip()
            warehouse_location = (warehouse_location.replace(' ', '')).split(',')
            warehouse_location = ';'.join([w.strip() for w in warehouse_location])
            all_products.append(f'{name}{delimiter}{warehouse_location}{delimiter}{get_date()}')    

        page = page + 1
        if len(product_list) < 500:
            break

    with open(shipstation_write_to, 'w') as p:
        p.write(f'name{delimiter}location{delimiter}date_retrived\n')
        for product in all_products:
            p.write(product + '\n')

#odoo
def write_to_odoo():
    products = odoo.search('product.product')
    fields = ['name', 'default_code', 'id', 'qty_available', 'categ_id']
    product_info = odoo.fields('product.product', products, fields)

    with open(odoo_write_to, 'w') as p:
        p.write(f'id{delimiter}name{delimiter}default_code{delimiter}qty_available{delimiter}categ_id{delimiter}date_retrived\n')
        for i in product_info:
            p.write(f"{i['id']}{delimiter}{i['name']}{delimiter}{i['default_code']}{delimiter}{int(i['qty_available'])}{delimiter}{i['categ_id']}{delimiter}{get_date()}" + '\n')

def main():
    print('Writing to Shipstation')
    write_to_shipstation()
    print('Writing to Odoo')
    write_to_odoo()

main()