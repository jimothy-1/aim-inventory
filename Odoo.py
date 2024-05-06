import requests
import json
import urllib.parse

class Odoo:
    def __init__(self, odoo_key, odoo_secret, base_url, access_token_path=None, refesh_token_path=None, print_succes=False):
        assert type(odoo_key) == str and type(odoo_secret) == str
        self.odoo_key = odoo_key
        self.odoo_secret = odoo_secret
        self.base_url = base_url if base_url[-1] != '/' else base_url[:-1] #take care of cases were url has slash at the end or not
        self.access_token_path = access_token_path if access_token_path else 'odoo_tokens\\access_token.txt'
        self.refresh_token_path = refesh_token_path if refesh_token_path else 'odoo_tokens\\refresh_token.txt'
        self.print_success = print_succes
    
    def read_access_token(self):
        with open(self.access_token_path, 'r') as a:
            access_token = a.read()
        return access_token

    def read_refresh_token(self):
        with open(self.refresh_token_path, 'r') as r:
            refresh_token = r.read()
        return refresh_token

    def write_odoo_tokens(self, access_token=None, refresh_token=None):
        if access_token:
            with open(self.access_token_path, 'w') as a:
                a.write(access_token)
        if refresh_token:
            with open(self.refresh_token_path, 'w') as r:
                r.write(refresh_token)

    def odoo_auth(self):
        url= f'{self.base_url}/restapi/1.0/common/oauth2/access_token'
        refresh_token = self.read_refresh_token()
        params= 'client_id=' + self.odoo_key + '&client_secret=' + self.odoo_secret + '&refresh_token=' + str(refresh_token) + '&grant_type=refresh_token'
        r= requests.post(url, headers={"Content-Type": "application/x-www-form-urlencoded"}, data=params)
        message = json.loads(r.text)

        if r.status_code == 200 and self.print_success:
            print('Odoo authentication successful')
        elif r.status_code != 200:
            print('Odoo authentication failed')

        self.write_odoo_tokens(message['access_token'], message['refresh_token'])

    def odoo_request(self, endpoint):
        self.odoo_auth()
        access_token = self.read_access_token()
        r = requests.get(self.base_url + endpoint,
            headers={'Accept':'application/json', "Authorization": 'Bearer ' + access_token})
        return json.loads(r.text)

    def search(self, odoo_object, search_type='', search_term=''):
        parsed_type = urllib.parse.quote(str(search_type).lower())
        parsed_term = urllib.parse.quote(search_term)
        domain = f"[('{parsed_type}','=','{parsed_term}')]" if parsed_term and parsed_type else "[]"
        endpoint = f"/restapi/1.0/object/{str(odoo_object)}/search?domain={domain}"

        search_items = self.odoo_request(endpoint)

        if odoo_object not in search_items: #partners['res.partner']:
            return False
        
        #print(f'Found a matching item for {odoo_object}')
        if len(search_items[odoo_object]) > 1:
            #print('Warning- multiple items found matching your search')
            pass
        return search_items[odoo_object] #odoo id
    
    def fields(self, odoo_object, ids=[], fields=[]):
        ids = ','.join(map(str, ids))
        fields = '[' + ','.join(map(str, [f"'{x}'" for x in fields])) + ']'
        endpoint = f"/restapi/1.0/object/{str(odoo_object)}?ids={ids}&fields={fields}"
        product = self.odoo_request(endpoint)
        if odoo_object in product:
            return product[odoo_object]
        return False
    

# erp_url = 'https://erp.aimdynamics.com'

# odoo_key = 'LPONkmPNibeba413OvxfiOyFFjVpzyMd'
# odoo_secret = 'x9pPnEb02uc2dju83xaeQbrqTV3CTc3a'

# odoo = Odoo(odoo_key, odoo_secret, erp_url)
# products = odoo.search('product.product')

# fields = ['name', 'default_code', 'id', 'qty_available', 'categ_id']
# product_info = odoo.fields('product.product', products, fields)
# print(product_info)