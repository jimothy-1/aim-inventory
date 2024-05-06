import requests
import json

class ShipStation:
    def __init__(self, shipstation_key, shipstation_secret):
        self.shipstation_key = shipstation_key
        self.shipstation_secret = shipstation_secret

    def row_and_number(self, warehouse_location):
        if not warehouse_location:
            return False, False, False
        
        try:
            warehouse_location = warehouse_location.split('-')
            letter = warehouse_location[0][0]
            row = warehouse_location[0][1:]
            length = warehouse_location[1]
            return letter, row, length
        except:
            return False, False, False
    
    def current_products(self):
        return_data = []

        page = 1
        while True:
            url = 'https://ssapi.shipstation.com/products?pageSize=500&page=' + str(page)
            r = requests.get(url, auth=(self.shipstation_key, self.shipstation_secret),
                    headers={'Accept':'application/json',"Content-Type":"application/json" })

            data = json.loads(r.text)
            product_list = data['products']
            pages = data['pages']

            for product in product_list:
                #check to make sure warehouse location exists
                warehouse_location = (product['warehouseLocation'].replace(' ', '')).split(',') if product['warehouseLocation'] else []
                warehouse_location = [w for w in warehouse_location if w]
                name = product['sku']
                if not warehouse_location or not name:
                    continue

                payload = {'name': name, 'warehouse_locations': warehouse_location}
                return_data.append(payload)

            if page >= pages:
                break
            page += 1

        return return_data
    
    def product(self, sku):
        url = f'https://ssapi.shipstation.com/products?sku={sku}'
        r = requests.get(url, auth=(self.shipstation_key, self.shipstation_secret),
            headers={'Accept':'application/json', 'Content-Type':'application/json'})
        products = (json.loads(r.text))['products']

        return_list = []
        #'abc' will match to 'abcdef', we want exact matches only
        for p in products:
            if p['sku'] == sku:
                return_list.append(p)

        return return_list

    def update_product(self, product):
        url = 'https://ssapi.shipstation.com/products/' + str(product['productId'])
        r = requests.put(url, auth=(self.shipstation_key, self.shipstation_secret),
            headers={"Content-Type":"application/json" }, data=json.dumps(product))
        
        return r.status_code == 200
