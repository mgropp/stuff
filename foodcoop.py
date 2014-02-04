#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import csv
import cgi
import argparse
from cookielib import CookieJar
from urllib2 import build_opener, HTTPCookieProcessor
from datetime import datetime

########################################################################
# URL für Tabelle als CSV
url = 'https://docs.google.com/spreadsheet/ccc?key=0ApNp0aXSrxXPdHlZYk1GTUtuVTVKVWd4RHpYY1ZPS2c&output=csv&gid=2'

# Zelle mit dem Lieferdatum
pos_date = (1,0)

# Zelle in der die Käufer beginnen, weitere Käufer rechts daneben
pos_customers = (5,4)

# Zelle mit dem ersten Hof
# Darunter:
# Zeilen, die nicht dem Muster (Ware, Preis?, Preis?, ...) entsprechen
# werden ignoriert.
# Nach Leerzeilen (=erste Spalte leer) beginnt ein neuer Hof.
pos_products = (10,0)
########################################################################

def get_cell(table, pos):
	(y, x) = pos
	return table[y][x]


def get_row(table, start):
	(y, x) = start
	return table[y][x:]


def to_float(s):
	try:
		return float(s)
	except:
		return None


def select_tuples(tuples, index, value, out_index=None):
	for t in tuples:
		if t[index] == value:
			if out_index is None:
				yield t
			else:
				yield t[out_index]


tuple_elements = ('supplier', 'product', 'customer', 'price_per_unit', 'quantity', 'unit', 'price')
tuple_indices = dict(zip(tuple_elements, range(len(tuple_elements))))


def encode_tuple(supplier, product, customer, price_per_unit, quantity, unit, price):
	return (supplier, product, customer, price_per_unit, quantity, unit, price)


def decode_tuple(t):
	return dict(zip(tuple_elements, t))


#f = open('test.csv')
opener = build_opener(HTTPCookieProcessor(CookieJar()))
f = opener.open(url)
try:
	table = list(tuple(row) for row in csv.reader(f))
finally:
	f.close()

date = get_cell(table, pos_date)
customers = get_row(table, pos_customers)

orders = []
products = []
suppliers = []

supplier = None
x_products = pos_products[1]
for y in range(pos_products[0], len(table)):
	row = table[y][x_products:]
	
	# Leerzeile
	if row[0] == "":
		supplier = None
		continue
	
	# Hof
	if supplier is None:
		supplier = row[0].strip().title()
		if supplier in suppliers:
			raise Exception('Mehrere Einträge für Hof: %s' % supplier)
			
		suppliers.append(supplier)
	
	(product, price_kg, price_piece) = row[0:3]
	price_kg = to_float(price_kg)
	price_piece = to_float(price_piece)
	
	# Zeile ignorieren?
	if (price_kg is None) and (price_piece is None):
		continue
	
	# Produkt!
	price_per_unit = price_kg if price_piece is None else price_piece
	unit = 'kg' if price_piece is None else 'Stück'
	if not product in products:
		products.append(product)
	
	for (customer, quantity) in zip(customers, row[pos_customers[1]:]):
		quantity = to_float(quantity)
		if (quantity is None) or (quantity <= 0):
			continue
		
		price = price_per_unit * quantity
		orders.append(encode_tuple(supplier, product, customer, price_per_unit, quantity, unit, price))


########################################################################
class FormatHtml(object):
	def __init__(self):
		self.out = ''
	
	def begin(self, title='Bestellung'):
		self.out += '<!DOCTYPE HTML><html><head><meta charset="UTF-8"><title>%s</title></head><body>\n' % cgi.escape(title)
		self.out += '<p><b>Warnung:</b> Das Programm, das diese Übersicht erzeugt, wurde noch nicht sehr gründlich getestet. Die Liste könnte also Fehler enthalten!</p>\n'

	def end(self):
		self.out += '</body></html>\n'
		
	def heading(self, s):
		self.out += '<h2>%s</h2>\n' % cgi.escape(s)

	def list_begin(self):
		self.out += '<ul>\n'

	def list_end(self):
		self.out += '</ul>\n'

	def customer_begin(self, customer, total):
		self.out += '<li><b>%s:</b> %.2f€\n<ul>\n' % (cgi.escape(customer), total)
	
	def customer_end(self):
		self.out += '</ul></li>\n'

	def supplier_begin(self, supplier, total):
		self.out += '<li><b>%s:</b> %.2f€\n<ul>\n' % (cgi.escape(supplier), total)
	
	def supplier_end(self):
		self.out += '</ul></li>\n'
	
	def product_customer(self, quantity, unit, product, supplier, price):
		product = cgi.escape(product)
		supplier = cgi.escape(supplier)
		self.out += '<li>%g %s %s von %s (%.2f€)</li>\n' % (quantity, unit, product, supplier, price)
	
	def product_supplier(self, quantity, unit, product, price_per_unit, price):
		product = cgi.escape(product)
		self.out += '<li>%g %s %s (à %.2f€): %.2f€</li>\n' % (quantity, unit, product, price_per_unit, price)


class FormatPlain(object):
	def __init__(self):
		self.out = ''
	
	def begin(self):
		self.out += 'WARNUNG: Das Programm, das diese Übersicht erzeugt, wurde noch nicht sehr gründlich getestet. Die Liste könnte also Fehler enthalten!\n'
		
	def end(self):
		self.out += ''
	
	def heading(self, s):
		self.out += '======== %s ========\n' % s

	def list_begin(self):
		self.out += ''

	def list_end(self):
		self.out += ''

	def customer_begin(self, customer, total):
		self.out += '%s: %.2f€\n' % (customer, total)
	
	def customer_end(self):
		self.out += '\n'
	
	def supplier_begin(self, supplier, total):
		self.out += '%s: %.2f€\n' % (supplier, total)
	
	def supplier_end(self):
		self.out += '\n'
	
	def product_customer(self, quantity, unit, product, supplier, price):
		self.out += '%g %s %s von %s (%.2f€)\n' % (quantity, unit, product, supplier, price)
	
	def product_supplier(self, quantity, unit, product, price_per_unit, price):
		self.out += '%g %s %s (à %.2f€): %.2f€\n' % (quantity, unit, product, price_per_unit, price)


class Mux(object):
	def __init__(self, *objects):
		self.objects = objects
		
		def makef(attr):
			def f(*args):
				for obj in objects:
					getattr(obj, attr)(*args)
			return f
		
		for obj in objects:
			for attr in dir(obj):
				if attr.startswith('__'):
					continue
				
				if hasattr(self, attr):
					continue
				
				if hasattr(getattr(obj, attr), '__call__'):
					setattr(self, attr, makef(attr))


def format_output(fmt):
	fmt.begin()
	
	# nach Kunde
	fmt.heading("Nach Kunden")
	fmt.list_begin()
	for customer in customers:
		tuples = list(select_tuples(orders, 2, customer))
		if len(tuples) == 0:
			continue
		
		total = sum(map(lambda x: x[-1], tuples))
		
		fmt.customer_begin(customer, total)
		for t in tuples:
			t = decode_tuple(t)
			fmt.product_customer(t['quantity'], t['unit'], t['product'], t['supplier'], t['price'])
		fmt.customer_end()

	fmt.list_end()


	# nach Hof
	fmt.heading("Nach Lieferanten")
	fmt.list_begin()
	for supplier in suppliers:
		tuples = list(select_tuples(orders, tuple_indices['supplier'], supplier))
		if len(tuples) == 0:
			continue

		total = sum(map(lambda x: x[tuple_indices['price']], tuples))
		
		fmt.supplier_begin(supplier, total)
		for product in products:
			product_tuples = list(select_tuples(tuples, tuple_indices['product'], product))
			if len(product_tuples) == 0:
				continue
			
			quantity = sum(map(lambda x: x[tuple_indices['quantity']], product_tuples))
			price = sum(map(lambda x: x[tuple_indices['price']], product_tuples))
			unit = product_tuples[0][tuple_indices['unit']]
			price_per_unit = product_tuples[0][tuple_indices['price_per_unit']]
			
			fmt.product_supplier(quantity, unit, product, price_per_unit, price)
		
		fmt.supplier_end()

	fmt.list_end()

	fmt.end()


########################################################################
parser = argparse.ArgumentParser(description='Foodcoop Bestellung')
parser.add_argument('--html', action='store_true', help='output HTML')
parser.add_argument('--mail', action='store_true', help='prepare output for sending by email (e.g. sendmail; including headers)')
parser.add_argument('--to', type=str, dest='recipient', action='store',  metavar='RECIPIENT', help='email recipient')
parser.add_argument('--from', type=str, dest='sender', action='store', metavar='SENDER', help='email sender')
parser.add_argument('--subject', type=str, default='Foodcoop-Bestellung KW %s' % datetime.now().isocalendar()[1], metavar='SUBJECT', action='store', help='email subject')

args = parser.parse_args()

if args.mail:
	if args.recipient is None or args.sender is None or args.subject is None:
		parser.error('Missing required --to/--from/--subject.')

if args.html:
	if not args.mail is None:
		out_html = FormatHtml()
		out_plain = FormatPlain()
		out = Mux(out_html, out_plain)
	else:
		out = FormatHtml()

else:
	out = FormatPlain()


format_output(out)


if args.mail:
	import StringIO
	import email
	from email.mime.multipart import MIMEMultipart
	from email.mime.text import MIMEText
	from email.header import Header
	from email.generator import Generator
	
	#email.Charset.add_charset('utf-8', email.Charset.QP, email.Charset.QP, 'utf-8')
	email.Charset.add_charset('utf-8', 'utf-8', 'utf-8', 'utf-8')
	
	multipart = MIMEMultipart('alternative')
	
	if all(ord(c) < 128 for c in args.sender):
		multipart['From'] = Header(args.sender)
	else:
		multipart['From'] = Header(args.sender, 'UTF-8').encode()
	
	if all(ord(c) < 128 for c in args.recipient):
		multipart['To'] = Header(args.recipient)
	else:
		multipart['To'] = Header(args.recipient, 'UTF-8').encode()
	
	if all(ord(c) < 128 for c in args.subject):
		multipart['Subject'] = Header(args.subject)
	else:
		multipart['Subject'] = Header(args.subject, 'UTF-8').encode()
	
	if args.html:
		multipart.attach(MIMEText(out_plain.out, 'plain', 'UTF-8'))
		multipart.attach(MIMEText(out_html.out, 'html', 'UTF-8'))
	else:
		multipart.attach(MIMEText(out.out, 'plain', 'UTF-8'))
	
	io = StringIO.StringIO()
	g = Generator(io, False)
	g.flatten(multipart)
	
	print(io.getvalue())

else:
	sys.stdout.write(out.out)
