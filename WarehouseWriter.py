import csv
import os
from datetime import datetime, timedelta
import shutil

file_information_seperator = '_' #keyword shelf, letter, date, time
delimiter = '\t'
time_to_complete = 100 #in days

qty_error = 'Quantity Mismatch'
add_product_error = 'Add Item'
remove_product_error = 'Remove Item'
saved_location_message = 'Save Location'

class WarehouseWriterShell:
    def __init__(self, writers=None):
        self.writers = writers if writers else []
        self.writers_dict = {w.shelf_letter:w for w in self.writers}
    
    def add_writer(self, writer):
        assert type(writer) == WarehouseWriter
        self.writers.append(writer)
        self.writers_dict[writer.shelf_letter] = writer

    def writer(self, shelf_letter):
        # if shelf_letter not in self.writers_dict:
        #     return False
        return self.writers_dict[shelf_letter.upper()]

class WarehouseWriter:
    def __init__(self, shelf_letter=None, file_extension=None, fields=None):
        self.fields = fields
        self.shelf_letter = shelf_letter.upper()
        self.file_extension = file_extension

        if shelf_letter and file_extension and fields:
            self.most_recent = False #if file already exists and is valid, most recent will contain a location
            self.file_name, is_new = self.create_path()
            self.path = f'{self.file_extension}{self.file_name}'

            if is_new:
                self.write_headers()

    #CONCERN- no clue if this works but we're gonna really hope so
    def initialize(self, shelf_letter, file_extension, fields):
        self.fields = fields
        self.shelf_letter = shelf_letter
        self.file_extension = file_extension

        self.most_recent = False #if file already exists and is valid, most recent will contain a location
        self.file_name, is_new = self.create_path()
        self.path = f'{self.file_extension}{self.file_name}'

        if is_new:
            self.write_headers()

    def create_path(self):
        #CONCERN- More of a thing to add, but basically fill in gaps with the file, work with next()
        #that way if they do some and then skip ahead and do some, we do the gaps

        #check if file exists
        def open_file(path):
            result = []
            with open(path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    result.append(row)

            return result
        
        def check_time(time):
            if not time:
                return False
            
            date_format = '%m-%d-%Y %H-%M-%S'
            current = datetime.now() #datetime.strptime(datetime.now(), date_format)
            
            time = time.replace(file_information_seperator, ' ')
            time = datetime.strptime(time, date_format)
            time_difference = abs(current - time)

            # Check if the time difference is within time to complete
            return time_difference <= timedelta(days=time_to_complete)

        path_files = os.listdir(self.file_extension)
        for path in path_files:
            p = path.split(file_information_seperator)
            if p[1].lower() != self.shelf_letter.lower():
                continue
            
            full_path = f'{self.file_extension}{path}'
            file_data = open_file(full_path)
            
            is_valid = False
            if file_data:
                is_valid = check_time(file_data[0]['date_modified'])
            #is file still within range of completion
            if is_valid:
                #CONCERN- indexing error causes most_recent to not exist or = ''
                #CONCERN- if for some reason there are multiple files for a single letter, it may cause some weird side effects
                self.most_recent = file_data[-1]['warehouse_location']
                return path, False
            #data is void because it is too old
            else:
                try:
                    print('Removing file')
                    os.remove(full_path)
                except:
                    print('Unable to remove old file')

        date = datetime.now().strftime(f'%m-%d-%Y{file_information_seperator}%H-%M-%S')
        #second return value is if it's new (true) or already existed (false)
        return f'shelf{file_information_seperator}{self.shelf_letter.upper()}{file_information_seperator}{date}.csv', True

    def write_headers(self):
        with open(self.path, 'w') as w:
            csvwriter = csv.writer(w, lineterminator = '\n')
            csvwriter.writerow(self.fields)

    def write_line(self, line_dict={}):
        field_dict = {field: None for field in self.fields}
        for line in line_dict:
            if line in self.fields:
                field_dict[line] = line_dict[line]

        with open(self.path, 'a') as w:
            csvwriter = csv.writer(w, lineterminator = '\n')
            csvwriter.writerow(list(field_dict.values()))

    def save_location(self, warehouse_location):
        d = {'warehouse_location': warehouse_location, 'error_type': 'Save Location', 'date_modified': datetime.now().strftime(f'%m-%d-%Y{file_information_seperator}%H-%M-%S')}
        self.write_line(d)

    def clear_file(self):
        with open(self.path, 'w') as w:
            w.write('')

    def write_error_lines(self, product_list, error_message, user_output=None):
        for product in product_list:
            product_fields = product.dict_view()
            product_fields['qty_available'] = product_fields['qty']
            product_fields['date_modified'] = datetime.now().strftime(f'%m-%d-%Y{file_information_seperator}%H-%M-%S')
            product_fields['error_type'] = error_message
            if user_output:
                product_fields['user_output'] = user_output

            self.write_line(product_fields)

    def compare_products_existence(self, new_bin, current_bin):
        #write if a product doesn't exist or if a new one was added
        def diff(bin1, bin2):
            #gives us a list of every product in bin1 not in bin2
            temp = []
            bin2_products = [product.name for product in bin2.products]
            for product in bin1.products:
                name = product.name
                if name not in bin2_products:
                    print(name, bin2_products)
                    temp.append(product)
            return temp
        
        products_removed = diff(current_bin, new_bin)
        products_added = [product for product in current_bin.products if product.is_added]

        self.write_error_lines(products_removed, remove_product_error)
        self.write_error_lines(products_added, add_product_error)

    def compare_qty(self, new_bin, current_bin):
        #check if qty is the same
        current_product_names = {product.name:product for product in current_bin.products}
        for product in new_bin.products:
            name = product.name
            qty = product.qty
            current_product = current_product_names[name]

            if qty and current_product.qty and int(current_product.qty) == int(qty):
                #the qty is good and doesn't need anything written
                continue

            self.write_error_lines([product], qty_error, qty)

    def clean_and_move(self, destination_path='finished_files/'):
        def move_file(destination_path):
            #check if shelf exists, if it does replace it
            path_files = os.listdir(destination_path)
            for path in path_files:
                full_path = f'{destination_path}{path}'
                letter = path.split(file_information_seperator)[1]
                if letter == self.shelf_letter:
                    os.remove(full_path)

            full_destination_path = f'{destination_path}{self.file_name}'
            shutil.move(self.path, full_destination_path)
            return full_destination_path

        def remove_saved():
            with open(self.path, 'r') as input_file:
                csv_reader = csv.DictReader(input_file)
                filtered_rows = [row for row in csv_reader if row.get('error_type') != 'Save Location']

            with open(self.path, 'w', newline='') as output_file:
                header = csv_reader.fieldnames
                csv_writer = csv.DictWriter(output_file, fieldnames=header)
                csv_writer.writeheader()
                csv_writer.writerows(filtered_rows)

        remove_saved()
        full_destination_path = move_file(destination_path)
        return full_destination_path

    def read_lines(self):
        pass

    def find_line(self):
        pass

    def saved_location(self):
        pass

    def complete_file(self):
        pass

class WarehouseReaderShell:
    def __init__(self, readers=None):
        self.readers = readers if readers else []
        self.readers_dict = {r.shelf_letter.upper():r for r in self.readers}

    def add_reader(self, reader):
        assert type(reader) == WarehouseReader
        self.readers_dict[reader.shelf_letter] = reader
        self.readers = [self.readers_dict[s] for s in self.readers_dict]

    def reader(self, shelf_letter):
        print(self.readers_dict)
        return self.readers_dict[shelf_letter.upper()]


class WarehouseReader:
    def __init__(self, filename=None, file_extension=None):
        #self.shelf_letter = shelf_letter.upper()
        self.file_extension = file_extension if file_extension else 'finished_files/'
        self.filename = filename
        self.path = f'{self.file_extension}{self.filename}'
        self.shelf_letter, self.date, self.time = self.filename_info()
        self.fields = self.get_fields()
        self.line = self.get_line()
        self.lines = self.get_lines()
        self.filesize = self.get_filesize()

    def get_fields(self):
        with open(self.path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                return list(row.keys())

    def get_line(self):
        #get the first line in the file
        with open(self.path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                return row

    def get_lines(self):
        l = []
        with open(self.path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                l.append(row)
        return l
    
    def get_filesize(self):
        self.filesize = len(self.get_lines())
        return self.filesize
    
    def filename_info(self):
        def add_time_of_day(time):
            if int(time[0]) > 12:   
                return str(int(time[0])-12) + ':' + str(time[1]) + ' PM'
            if int(time[0]) == 12:
                return str(int(time[0])) + ':' + str(time[1]) + ' PM'
            return str(int(time[0])) + ':' + str(time[1]) + ' AM'
    
        f = self.filename.split(file_information_seperator)

        #shelf letter, date, time
        return f[1], f[2], add_time_of_day(f[3][:-4].split('-'))
    
    def write_to_file(self, lines):
        with open(self.path, 'w', newline='') as output_file:
            csv_writer = csv.DictWriter(output_file, fieldnames=self.fields)
            csv_writer.writeheader()
            csv_writer.writerows(lines)

    def skip_line(self):
        line = self.get_line()
        lines = self.get_lines()
        #remove line and add to the end
        lines.remove(line)
        lines.append(line)

        self.write_to_file(lines)
        #update line
        self.line = self.get_line()

    def delete_line(self):
        line = self.get_line()
        lines = self.get_lines()
        #remove line
        lines.remove(line)

        self.write_to_file(lines)
        #update line
        self.line = self.get_line()

class Line:
    def __init__(self, line_data):
        self.line_data = line_data
        self.warehouse_location = self.line_data['warehouse_location']
        self.name = self.line_data['name']
        self.qty = self.line_data['qty'] if self.line_data['qty'] else 'Unknown'
        self.odoo_id = self.line_data['odoo_id'] if self.line_data['odoo_id'] else 'Unknown'
        self.user_output = self.user_output