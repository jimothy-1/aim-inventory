class Warehouse:
    def __init__(self, shelfs=None):
        self.shelfs = shelfs if shelfs else {}
        self.shelf_letters = self.get_shelf_letters()

    def __str__(self):
        for s in self.shelfs:
            return f'{s}: {self.shelfs}'
        return 'Warehouse is empty'
    
    def get_shelf_letters(self):
        return [s for s in self.shelfs]

    def add_shelf(self, shelf):
        self.shelfs[shelf.shelf_letter] = shelf
        self.shelf_letters = self.get_shelf_letters()

    def shelf(self, shelf_letter):
        #CONCERN- This doesn't work when not loaded from a file?
        assert shelf_letter.upper() in self.shelf_letters
        return self.shelfs[shelf_letter.upper()]
    
    def clear_shelf(self, shelf_letter):
        # for shelf in self.shelfs:
        #     self.shelfs[shelf] = Shelf(self.shelfs[shelf].shelf_letter, self.shelfs[shelf].rows, self.shelfs[shelf].length)
        shelf_letter = shelf_letter.upper()
        self.shelfs[shelf_letter] = Shelf(self.shelfs[shelf_letter].shelf_letter, self.shelfs[shelf_letter].rows, self.shelfs[shelf_letter].length)

    def change_shelf(self, shelf_letter, shelf):
        self.shelfs[shelf_letter] = shelf

    def expand_warehouse(self):
        #basically expand all shelfs
        pass

class Shelf:
    def __init__(self, shelf_letter, rows, length):
        self.shelf_letter = shelf_letter.upper()
        self.rows = rows
        self.length = length
        self.inventory = self.create_shelf()
        self.bin_locations = [x for x in self.inventory]

    def __str__(self):
        return f'Shelf {self.shelf_letter}, {self.rows*self.length} spots'

    def create_shelf(self):
        #CONCERN - especially for the r < 9, this could easily be rewritten to be much shorter
        #it could also use the shelf_id function for further simplification and dynamic-ness
        array = []
        dictionary = {}
        for j in range(self.rows):
            for r in range(self.length):
                item_space = str(r+1)
                if r < 9:
                    item_space = '0' + str(r+1)

                warehouse_space = self.shelf_letter.upper() + str(j+1) + '-' + item_space
                array.append(warehouse_space)

                dictionary[warehouse_space] = Bin(self, warehouse_space)

        return dictionary
    
    def expand_overview(self):
        for location in self.inventory:
            for product in self.inventory[location].products:
                print(product.warehouse_location, product.name, product.qty)

    def shelf_id(self, row, number):
        #return f'{self.shelf_letter}{row}-{number:02}'
        formatted_number = "{num:0>2}".format(num=number)
        return f'{self.shelf_letter}{row}-{formatted_number}'

    def get_bin(self, location=None, row=None, number=None):
        if location:
            print(location)
            assert '-' in location
            assert type(location) == str
            search = location.upper()
        else:
            search = self.shelf_id(row, number)
        if search in self.inventory:
            assert type(self.inventory[search]) == Bin
            return self.inventory[search]
        return False
    
    def find_product(self, name):
        bins = [self.inventory[a] for a in self.inventory]
        products = [product for bin in bins for product in bin.products]

        product_names = {p.name: p for p in products}
        if name in product_names:
            return product_names[name]
        return False
    
    def first_item(self):
        return self.inventory[self.bin_locations[0]]

    def next_item(self, current_bin):
        assert current_bin.location in self.bin_locations
        assert type(current_bin) == Bin

        new_index = self.bin_locations.index(current_bin.location) + 1

        #if last item in warehouse
        if new_index == len(self.bin_locations):
            return False #'finished'
        
        return self.inventory[self.bin_locations[new_index]]
    
    def compare_bins(bin1, bin2):
        #when they enter new data, lets make that data into a bin
        #we can then compare the bins and spit out the differences
        pass

class Bin:
    def __init__(self, shelf, location, products=None):
        self.shelf = shelf
        self.location = location
        self.products = products if products is not None else []
        self.bin_length = len(self.products)

    def add_product(self, product):
        self.products.append(product)
        product.warehouse_location = self.location
        #self.shelf.inventory[self.location] = self
        self.bin_length = len(self.products)
    
    def remove_product(self, product):
        self.products.remove(product)
        self.bin_length = len(self.products)
    
    def get_product(self):
        #get product info too?
        pass

    def find_product_by_name(self, name):
        for product in self.products:
            if product.name == name:
                return product
        return False