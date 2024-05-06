class Product:
    def __init__(self, name=None, qty=None, odoo_id=None, warehouse_location=None, warehouse_locations=None, master_location=None, is_added=None):
        self.name = name
        self.qty = qty
        self.odoo_id = odoo_id
        self.warehouse_location = warehouse_location
        
        self.warehouse_locations = warehouse_locations if warehouse_locations else []
        if self.warehouse_location and self.warehouse_location not in self.warehouse_locations:
            self.warehouse_locations.append(self.warehouse_location)

        self.master_location = self.warehouse_location if self.warehouse_location else master_location
        if len(self.warehouse_locations) >= 1:
            self.master_location = self.warehouse_locations[0]
        self.master_location = master_location if master_location else self.master_location

        self.is_added = is_added if is_added else False

    def __str__(self):
        return f'{self.qty} of {self.name} in {self.warehouse_location} with Odoo id {self.odoo_id}'

    def copy_product(self):
        return Product(
            name=self.name,
            qty=self.qty,
            odoo_id=self.odoo_id,
            warehouse_location=self.warehouse_location,
            warehouse_locations=self.warehouse_locations,
            master_location=self.master_location,
            is_added=self.is_added
        )

    def set_warehouse_location(self, warehouse_location):
        assert type(warehouse_location) == str
        self.warehouse_location = warehouse_location
        if self.warehouse_location not in self.warehouse_locations:
            self.warehouse_locations.append(self.warehouse_location)
        if not self.master_location:
            self.master_location = self.warehouse_location

    def dict_view(self):
        d = {
            'name': self.name,
            'qty': self.qty,
            'odoo_id': self.odoo_id,
            'warehouse_location': self.warehouse_location,
            'master_location': self.master_location
        }

        return d

    def is_master(self):
        return self.master_location == self.warehouse_location and self.master_location and self.warehouse_location

    def warehouse_locations_str(self):
        return ', '.join(self.warehouse_locations)

    def set_name(self, name):
        assert type(name) == str
        self.name = name

    def set_odoo_id(self, odoo_id):
        assert type(odoo_id) == int
        self.odoo_id = odoo_id

    def set_qty(self, qty):
        assert type(qty) == int
        self.qty = qty

    def write_to_csv(self):
        return f'{self.warehouse_location},{self.name},{self.odoo_id},{self.qty}'
    
    def save_data(self, filename):
        with open(filename, 'a') as f:
            f.write(self.write_to_csv())
