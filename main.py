from flask import Flask, render_template, redirect, url_for, render_template, request, session, send_file
import requests
import json
import csv
import datetime
from email.message import EmailMessage
import ssl
import smtplib
import os
import shutil
from csv import writer
import random

from Odoo import Odoo
from Warehouse import *
from Product import Product
from Shipstation import ShipStation
from WarehouseWriter import *

from datetime import datetime, timedelta

# #list of all products in the shelf, used by the website to display info on the screen
# shelf_products = []
# counter = 0

erp_url = 'https://erp.aimdynamics.com'
odoo_key = 'LPONkmPNibeba413OvxfiOyFFjVpzyMd'
odoo_secret = 'x9pPnEb02uc2dju83xaeQbrqTV3CTc3a'
odoo = Odoo(odoo_key, odoo_secret, erp_url)

shipstation_key = 'e081490e668640a58cacb1a061d33373'
shipstation_secret = '64ae04ab98a3485fa45c86b184c58679'
shipstation = ShipStation(shipstation_key, shipstation_secret)

warehousewritershell = WarehouseWriterShell()
warehousereadershell = WarehouseReaderShell()

shipstation_data_read_path = 'product_data/shipstation.csv'
odoo_data_read_path = 'product_data/odoo.csv'

delimiter='\t'
hour_diff = 7 #allowed difference between time retrived and current time (in hours)

file_folder_path = 'files/' #include /
fields = ['warehouse_location', 'name', 'default_code', 'owner', 'odoo_id', 'qty_available', 'error_type', 'user_output', 'date_modified']

def config():
    with open('config.json', 'r') as c:
        return json.loads(c.read())
def write_config(key, value):
    file = config()
    file[key] = value
    with open('config.json', 'w') as c:
        c.write(json.dumps(file, indent=4))

def email_receiver():
    return str(config()['EmailSupport'])

warehouse = Warehouse()
warehouse.add_shelf(Shelf('A',5,24))
warehouse.add_shelf(Shelf('B',5,36))
warehouse.add_shelf(Shelf('C',5,36))
warehouse.add_shelf(Shelf('D',5,24))
warehouse.add_shelf(Shelf('E',5,24))
warehouse.add_shelf(Shelf('F',5,24))
warehouse.add_shelf(Shelf('G',5,28))

def fill_shelf_shipstation(shelf):
    current_products = shipstation.current_products()

    for product in current_products:
        name = product['name']
        warehouse_locations = product['warehouse_locations']
        for w in warehouse_locations:
            letter, row, number = shipstation.row_and_number(w)
            if not row or not number or letter != shelf.shelf_letter:
                continue

            shelf_bin = shelf.get_bin(row=row, number=number)
            if shelf_bin:
                #CHANGE- removed warehouse_location= because bin should do that
                p = Product(name=name, warehouse_locations=warehouse_locations)
                shelf_bin.add_product(p)

    return shelf

def fill_shelf_odoo(shelf):
    products = odoo.search('product.product')

    fields = ['name', 'default_code', 'id', 'qty_available', 'categ_id']
    product_info = odoo.fields('product.product', products, fields)
    #if there is a default code do we use it? yes as of 12/28/23 (Victor)
    default_codes = {x['default_code'] if x['default_code'] else x['name']: x for x in product_info}

    for location in shelf.inventory:
        bin = shelf.inventory[location]
        for product in bin.products:
            product_name = product.name
            if product_name in default_codes:
                qty = int(default_codes[product_name]['qty_available']) if default_codes[product_name]['qty_available'] else 0
                product.set_qty(qty)
                product.set_odoo_id(int(default_codes[product_name]['id']))

    return shelf

def load_shelf(shelf):
    #if no recent data, call api, otherwise just read file to save SO MUCH TIME
    def check_time(time):
        date_format = "%Y-%m-%d %H:%M:%S"
        current = datetime.now() #datetime.strptime(datetime.now(), date_format)
        time = datetime.strptime(time, date_format)
        time_difference = abs(current - time)

        # Check if the time difference is within one hour
        return time_difference <= timedelta(hours=hour_diff)
    
    def open_file(path):
        with open(path, 'r') as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=delimiter)
            header = next(csv_reader, None)
            #convert bools to bools before transforming
            ship_data = [{h: r for h, r in zip(header, [True if value.lower() == 'true' else False if value.lower() == 'false' else value for value in row])} for row in csv_reader]
        return ship_data
    
    def valid_time(data, times=[]):
        for time in times:
            if not check_time(time):
                return False
        return data

    def read_shipstation():
        ship_data = open_file(shipstation_data_read_path)
        return valid_time(ship_data, [ship_data[0]['date_retrived'], ship_data[-1]['date_retrived']])

    def read_odoo():
        odoo_data = open_file(odoo_data_read_path)
        return valid_time(odoo_data, [odoo_data[0]['date_retrived'], odoo_data[-1]['date_retrived']])

    ship_data = read_shipstation()
    odoo_data = read_odoo()

    #retrive shipstation data
    if not ship_data:
        print('Shipstation data not recent, retriving from API')
        shelf = fill_shelf_shipstation(shelf)
    else:
        #add in ship data from file
        print('Using data from Shipstation file')
        for product in ship_data:
            #check to make sure warehouse location exists
            warehouse_location = product['location']
            name = product['name']
            warehouse_location = warehouse_location.split(';')

            for w in warehouse_location:
                letter, row, number = shipstation.row_and_number(w)
                if not row or not number or letter != shelf.shelf_letter:
                    continue

                shelf_bin = shelf.get_bin(row=row, number=number)
                if shelf_bin:
                    #CHANGE- removed warehouse_location= because bin should do that
                    p = Product(name=name, warehouse_locations=warehouse_location)
                    shelf_bin.add_product(p)

    #retrive odoo data
    if not odoo_data:
        print('Odoo data not recent, retriving from API')
        shelf = fill_shelf_odoo(shelf)
    else:
        #add in odoo data from file
        print('Using data from Odoo file')

        with open('text_file.txt', 'w') as t:
            for line in odoo_data:
                t.write(str(line) + '\n')
        default_codes = {x['default_code'] if x['default_code'] else x['name']: x for x in odoo_data}
        with open('text_default_codes.json', 'w') as t:
            t.write(json.dumps(default_codes, indent=4))
        for location in shelf.inventory:
            bin = shelf.inventory[location]
            for product in bin.products:
                product_name = product.name
                if product_name in default_codes:
                    qty = int(default_codes[product_name]['qty_available']) if default_codes[product_name]['qty_available'] else 0
                    product.set_qty(qty)
                    product.set_odoo_id(int(default_codes[product_name]['id']))

def load_product(name):   
    #CONCERN- don't love the try-except, but keep it this way until more testing 
    try:
        shipstation_product = shipstation.product(name)
        #CONCERN- investigate this more, could we still find the correct product even with multiple search results?
        if not shipstation_product or len(shipstation_product) > 1:
            return Product(name=name, is_added=True)
        
        fields = ['name', 'default_code', 'id', 'qty_available', 'categ_id']
        odoo_product = odoo.search('product.product', 'default_code', name)
        #CONCERN- investigate this more, could we still find the correct product even with multiple search results?
        if not odoo_product or len(odoo_product) > 1:
            return Product(name=name, is_added=True)
        
        shipstation_product = shipstation_product[0]
        odoo_product = odoo.fields('product.product', [odoo_product[0]], fields)
        
        name = shipstation_product['sku']
        qty = int(odoo_product['qty_available']) if odoo_product['qty_available'] else None
        warehouse_locations = (shipstation_product['warehouseLocation'].replace(' ', '')).split(',') if shipstation_product['warehouseLocation'] else []
        return Product(name=name, warehouse_locations=warehouse_locations, qty=qty, odoo_id=odoo_product['id'], is_added=True)
    except:
        return Product(name=name, is_added=True)

def email(subject, body, email_receiver, file_path=None):
    email_sender = 'sales@aimdynamics.com' #'jameschem27@gmail.com'
    email_password = 'Aim#9Magnets!' #'awcdhrdxfizirqqj' #this is for jameschem27

    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = email_receiver
    em['Subject'] = subject
    em.set_content(body)
    
    if file_path:
        with open(file_path, 'rb') as content_file:
            content = content_file.read()
            abbreviated_path = file_path.split('/')[1]
            em.add_attachment(content, maintype='application', subtype='csv', filename=abbreviated_path)

    # Add SSL (layer of security)
    context = ssl.create_default_context()

    # Log in and send the email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, [em['To']], em.as_string())
        print('Emailed!')
        #[email_receiver]+em['Cc']

#run app
app = Flask(__name__)

#home page
@app.route('/')
def home():
    #session['mode'] = 'maverick' #admin mode
    #remove_unused_files("./files/", 5)
    return render_template('home.html', warehouse=warehouse)

@app.route('/<shelf_letter>', methods=['GET', 'POST'])
def shelf(shelf_letter):
    #CONCERN- would it be better to make this it's own function, this function calls that
    #and if shelf data is missing it will automatically grab it
    warehouse.clear_shelf(shelf_letter)
    shelf_class = warehouse.shelf(str(shelf_letter))
    load_shelf(shelf_class)

    #create file
    if shelf_letter.upper() in warehouse.shelf_letters: #if shelf in ['A', 'B', 'C', etc...]
        warehousewriter = WarehouseWriter(shelf_letter, file_folder_path, fields)
        warehousewritershell.add_writer(warehousewriter)
        #warehousewriter.initialize(shelf_letter, file_folder_path, fields)

    #if the file is new, it starts from beginning
    #if it already exists, it will start at most_recent
    print(warehousewriter.most_recent)
    starting_location = warehousewriter.most_recent if warehousewriter.most_recent else shelf_class.first_item().location
    return redirect(f'/{shelf_letter.lower()}/{starting_location}')

@app.route('/<shelf_letter>/<location>', methods=['GET', 'POST'])
def check_location(shelf_letter, location):
    if location == 'finished':
        return redirect(f'/finished/{shelf_letter.upper()}')

    shelf = warehouse.shelf(shelf_letter)
    current_bin = shelf.get_bin(location=location)

    warehousewriter = warehousewritershell.writer(shelf_letter)
    warehousewriter.save_location(location)
    return render_template('shelf_location.html', bin_data=current_bin, shelf=shelf_letter.upper(), shelf_code=location.upper())

@app.route('/add-product/<shelf_letter>/<location>', methods=['GET', 'POST'])
def add_product(shelf_letter, location):
    if request.method == 'POST':
        shelf = warehouse.shelf(shelf_letter)
        current_bin = shelf.get_bin(location=location)

        product_name = request.form.get('textbox_name')
        if product_name and product_name not in [product.name for product in current_bin.products]:
            #load in information if possible
            #product = Product(name=product_name, is_added=True)
            product = load_product(product_name)
            current_bin.add_product(product)

        #CONCERN- I would like the radio button state to be saved when redirected
        return redirect(f'/{shelf_letter}/{location}')

    products = []
    with open(shipstation_data_read_path, 'r') as csvreader:
        csv_reader = csv.DictReader(csvreader, delimiter=delimiter)
        for line in csv_reader:
            name = line['name']
            if name:
                products.append(name)
    
    return render_template('add_product.html', products=products, shelf_letter=shelf_letter, location=location)

@app.route('/<shelf_letter>/<location>/qty', methods=['GET', 'POST'])
def check_qty(shelf_letter, location):
    shelf = warehouse.shelf(shelf_letter)
    current_bin = shelf.get_bin(location=location)

    if request.method == 'POST':
        key_value = {'-'.join(key.split('-')[1:]):True if value == 'true' else False for key, value in request.form.items()}
        #bin of products that need qty check
        qty_bin = Bin(shelf_letter, location)
        #bin of products to be compared to the current_bin
        compare_bin = Bin(shelf_letter, location)
        for item in key_value:
            #if they selected True
            if key_value[item]:
                p = current_bin.find_product_by_name(item)
                if p.is_master() or p.is_added:
                    qty_bin.add_product(p)
                compare_bin.add_product(p)

        #compare bins and write new products, removed products
        warehousewriter = warehousewritershell.writer(shelf_letter)
        warehousewriter.compare_products_existence(compare_bin, current_bin)

        if qty_bin.products:
            return render_template('shelf_qty.html', bin_data=qty_bin,shelf=shelf_letter.upper(), shelf_code=location.upper(), times_visited=0)
        #if nothing is master then just skip
        location = shelf.next_item(current_bin).location if shelf.next_item(current_bin) else 'finished'
        return redirect(f'/{shelf_letter}/{location}')
    
    #CONCERN- this function is a little weird, and this next part is just a precaution
    #if they get to this page without posting the data it would error
    #so my thought is the only way this would happen is during testing OR
    #this is where they resume. Thinking about it, make sure they always resume on step ONE.
    #unless in the future you want to read passed and failed products to create a new bin.
    #interesting idea.
    return render_template('shelf_qty.html', bin_data=current_bin,shelf=shelf_letter.upper(), shelf_code=location.upper(), times_visited=0)

@app.route('/<shelf_letter>/<location>/process-qty/<times_visited>', methods=['POST'])
def process_qty(shelf_letter, location, times_visited):
    times_visited = int(times_visited)

    shelf = warehouse.shelf(shelf_letter)
    current_bin = shelf.get_bin(location=location)

    key_value = {'-'.join(key.split('-')[1:]): int(value) if value.isdigit() else 0 for key, value in request.form.items()}

    new_bin = Bin(shelf_letter, location)
    review_bin = Bin(shelf_letter, location)
    for item in key_value:
        qty = key_value[item]
        product = current_bin.find_product_by_name(item)
        odoo_qty = product.qty
    
        #new_product = Product(product.name, qty=qty)
        new_product = product.copy_product()
        new_product.set_qty(qty)

        new_bin.add_product(new_product)

        if odoo_qty == qty:
            continue

        review_bin.add_product(product)

    #if everything matches or new product with no other data
    if not review_bin.products or times_visited:
        #compare qtys before moving on, shouldn't matter if they're the same
        warehousewriter = warehousewritershell.writer(shelf_letter)
        warehousewriter.compare_qty(new_bin, current_bin)
        next_location_name = (shelf.next_item(current_bin)).location if type(shelf.next_item(current_bin)) == Bin else 'finished' #(shelf.next_item(current_bin))
        return redirect(f'/{shelf_letter}/{next_location_name}')

    #redirect to the next item
    return render_template('shelf_qty.html', bin_data=review_bin,shelf=shelf_letter.upper(), shelf_code=location.upper(), times_visited=1)

@app.route('/finished/<shelf_letter>')
def finished(shelf_letter):
    shelf_letter = shelf_letter.upper()
    warehousewriter = warehousewritershell.writer(shelf_letter)
    destination_path = warehousewriter.clean_and_move()
    body = "Here's a backup file for the completed shelf"
    receiver = email_receiver()
    email(f'Shelf {shelf_letter} Inventory', body, receiver, destination_path)
    return render_template('finished.html', shelf_letter=shelf_letter, link='/')

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html'), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

#admin
@app.route('/change-email', methods=['GET', 'POST'])
def change_email():
    if request.method == 'POST':
        email = request.form.get('textbox')
        email = email if email else email_receiver()
        write_config('EmailSupport', str(email))
        return redirect('/admin')
    return render_template('enter_email.html', saved_email_address=email_receiver())

@app.route('/admin')
def admin_home():
    def num_lines(file_path):
        with open(file_path, 'r') as input_file:
            csv_reader = csv.DictReader(input_file)
            return sum(1 for line in csv_reader)
    
    file_path = "finished_files/"

    path_files = os.listdir(file_path)
    for path in path_files:
        if num_lines(f'{file_path}{path}') == 0:
            os.remove(f'{file_path}{path}')
            continue

        warehousereader = WarehouseReader(path, file_path)
        warehousereadershell.add_reader(warehousereader)

    return render_template('admin_home.html', warehousereadershell=warehousereadershell)

@app.route('/email-file/<shelf_letter>')
def email_finished_file(shelf_letter):
    #IDEA- what if instead this just downloaded it straight to your computer
    filereader = warehousereadershell.reader(shelf_letter)
    path = filereader.path
    #body = "Here's a backup file for the completed shelf"
    #receiver = email_receiver()
    #email(f'Shelf {shelf_letter} Inventory', body, receiver, path)
    return send_file(path, as_attachment=True, download_name=f'shelf_{shelf_letter.upper()}.csv')
    #return redirect('/admin')

@app.route('/review-file/<shelf_letter>', methods=['GET', 'POST'])
def admin_main(shelf_letter):
    warehousereader = warehousereadershell.reader(shelf_letter)

    if request.method == 'POST':
        #respond to action
        button_value = request.form['action']

        #update shipstation
        if button_value == 'shipstation':
            update_product_locations(warehousereader.get_line())
            warehousereader.delete_line()
        #skip
        if button_value == 'skip':
            warehousereader.skip_line()
        #mark as complete
        if button_value == 'complete':
            warehousereader.delete_line()

        #make sure reader not empty
        if warehousereader.is_complete():
            return redirect(f'/finished-admin/{shelf_letter.upper()}')

        #get next line
        return render_template('admin_main.html', warehousereader=warehousereader)


    return render_template('admin_main.html', warehousereader=warehousereader)

    #options are update, skip, delete
    #go to next item in the file

def update_product_locations(line):
    #{'default_code': '', 'error_type': 'Quantity Mismatch', 'name': 'ACT-0036-200', 'odoo_id': '', 'owner': '', 'qty_available': '', 'status': 'New', 'user_output': '123', 'warehouse_location': 'C1-03'}
    sku, location, error_type = line['name'], line['warehouse_location'], line['error_type']
    product = shipstation.product(sku)

    if len(product) > 1 or len(product) == 0:
        return False
    
    #product should be a [] with 1 item
    product = product[0]
    #CONCERN- Had to wrap this in a try-except statement in old version
    warehouse_location = (product['warehouseLocation']).replace(' ', '')
    warehouse_location = [w for w in warehouse_location.split(',') if w]

    if error_type == 'Add Item':
        if location not in warehouse_location:
            warehouse_location.append(location)
    elif error_type == 'Remove Item':
        if location in warehouse_location:
            warehouse_location.remove(location)

    #CONCERN- in old version I sort the list after the first, doesn't feel neccassary
    product['warehouseLocation'] = (', ').join(warehouse_location)

    #true if update successful
    return shipstation.update_product(product)

@app.route('/finished-admin/<shelf_letter>')
def finished_admin(shelf_letter):
    shelf_letter = shelf_letter.upper()
    warehousereadershell.remove_reader(shelf_letter)
    return render_template('finished.html', shelf_letter=shelf_letter, link='/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
