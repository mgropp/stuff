#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# mgropp, 2014-02-12
from __future__ import print_function
import sys
import csv
import cgi
import argparse
import math
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


def to_cents(s):
	try:
		if '.' in s:
			(euros, cents) = tuple(s.split('.'))
			if len(cents) < 2:
				cents += '0'
			elif len(cents) > 2:
				return None
			
			return 100*int(euros) + int(cents)
		else:
			return 100 * int(s)
		
	except:
		return None


def cents_to_euros(cents):
	euros = math.ceil(cents) / 100.0
	rounded = abs(cents/100.0 - euros) > 0.00001
	if rounded:
		rounded = -1 if (euros < cents / 100.0) else 1
	return (euros, rounded)


def select_tuples(tuples, index, value, out_index=None):
	for t in tuples:
		if t[index] == value:
			if out_index is None:
				yield t
			else:
				yield t[out_index]


tuple_elements = ('supplier', 'product', 'customer', 'price_per_unit', 'quantity', 'unit')
tuple_indices = dict(zip(tuple_elements, range(len(tuple_elements))))


def encode_tuple(supplier=None, product=None, customer=None, price_per_unit=None, quantity=None, unit=None):
	return (supplier, product, customer, price_per_unit, quantity, unit)


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
customers = map(lambda x: x.strip(), get_row(table, pos_customers))

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
	price_kg = to_cents(price_kg)
	price_piece = to_cents(price_piece)
	
	# Zeile ignorieren?
	if (price_kg is None) and (price_piece is None):
		continue
	
	# Produkt!
	product = product.strip()
	price_per_unit = price_kg if price_piece is None else price_piece
	unit = 'kg' if price_piece is None else 'Stück'
	if not product in products:
		products.append(product)
	
	for (customer, quantity) in zip(customers, row[pos_customers[1]:]):
		quantity = to_float(quantity)
		if (quantity is None) or (quantity <= 0):
			continue
		
		orders.append(encode_tuple(supplier, product, customer, price_per_unit, quantity, unit))


########################################################################
class FormatHtml(object):
	def __init__(self):
		self.out = ''
	
	def __enter__(self):
		title = 'Bestellung'
		self.out += '<!DOCTYPE HTML><html><head><meta charset="UTF-8"><title>%s</title></head><body>\n' % cgi.escape(title)
		self.out += '<p><b>Warnung:</b> Das Programm, das diese Übersicht erzeugt, wurde noch nicht sehr gründlich getestet. Die Liste könnte also Fehler enthalten!</p>\n'
		return self
	
	def __exit__(self, *exc_info):
		self.out += '</body></html>\n'
	
	def heading(self, s):
		self.out += '<h2>%s</h2>\n' % cgi.escape(s)
	
	def list(oself):
		class List(object):
			def __enter__(iself):
				oself.out += '<ul>\n'
				return iself
			
			def __exit__(iself, *exc_info):
				oself.out += '</ul>\n'
		
		return List()
	
	def customer(oself, customer, total, rounded=0):
		class Customer(object):
			def __enter__(iself):
				if rounded != 0:
					oself.out += '<li><b>%s:</b> ≈%.2f€%s\n<ul>\n' % (cgi.escape(customer), total, '↓' if rounded < 0 else '↑')
				else:
					oself.out += '<li><b>%s:</b> %.2f€\n<ul>\n' % (cgi.escape(customer), total)
				return iself
	
			def __exit__(iself, *exc_info):
				oself.out += '</ul></li>\n'
		
		return Customer()
	
	def supplier(oself, supplier, total, rounded=0):
		class Supplier(object):
			def __enter__(iself):
				if rounded != 0:
					oself.out += '<li><b>%s:</b> ≈%.2f€%s\n<ul>\n' % (cgi.escape(supplier), total, '↓' if rounded < 0 else '↑')
				else:
					oself.out += '<li><b>%s:</b> %.2f€\n<ul>\n' % (cgi.escape(supplier), total)
				return iself
	
			def __exit__(iself, *exc_info):
				oself.out += '</ul></li>\n'
		
		return Supplier()
	
	def product_customer(self, quantity, unit, product, supplier, price, rounded=0):
		product = cgi.escape(product)
		supplier = cgi.escape(supplier)
		if rounded != 0:
			self.out += '<li>%g %s %s von %s (≈%.2f€%s)</li>\n' % (quantity, unit, product, supplier, price, '↓' if rounded < 0 else '↑')
		else:
			self.out += '<li>%g %s %s von %s (%.2f€)</li>\n' % (quantity, unit, product, supplier, price)
	
	def product_supplier(self, quantity, unit, product, price_per_unit, price, rounded=0):
		product = cgi.escape(product)
		if rounded != 0:
			self.out += '<li>%g %s %s (à %.2f€): ≈%.2f€%s</li>\n' % (quantity, unit, product, price_per_unit, price, '↓' if rounded < 0 else '↑')
		else:
			self.out += '<li>%g %s %s (à %.2f€): %.2f€</li>\n' % (quantity, unit, product, price_per_unit, price)


class FormatPlain(object):
	def __init__(self):
		self.out = ''
	
	def __enter__(self):
		self.out += 'WARNUNG: Das Programm, das diese Übersicht erzeugt, wurde noch nicht sehr gründlich getestet. Die Liste könnte also Fehler enthalten!\n\n'
		return self
		
	def __exit__(self, *exc_info):
		self.out += ''
	
	def heading(self, s):
		self.out += '======== %s ========\n' % s

	def list(self):
		class List(object):
			def __enter__(self):
				return self
			def __exit__(self, *exc_info):
				pass
		
		return List()

	def customer(oself, customer, total, rounded=0):
		class Customer(object):
			def __enter__(iself):
				if rounded != 0:
					oself.out += '%s: ≈%.2f€%s\n' % (customer, total, '↓' if rounded < 0 else '↑')
				else:
					oself.out += '%s: %.2f€\n' % (customer, total)
				return iself
				
			def __exit__(iself, *exc_info):
				oself.out += '\n'
		
		return Customer()
	
	def supplier(oself, supplier, total, rounded=0):
		class Supplier(object):
			def __enter__(iself):
				if rounded != 0:
					oself.out += '%s: ≈%.2f€%s\n' % (supplier, total, '↓' if rounded < 0 else '↑')
				else:
					oself.out += '%s: %.2f€\n' % (supplier, total)
				return iself
	
			def __exit__(iself, *exc_info):
				oself.out += '\n'
		
		return Supplier()
	
	def product_customer(self, quantity, unit, product, supplier, price, rounded=0):
		if rounded != 0:
			self.out += '%g %s %s von %s (≈%.2f€%s)\n' % (quantity, unit, product, supplier, price, '↓' if rounded < 0 else '↑')
		else:
			self.out += '%g %s %s von %s (%.2f€)\n' % (quantity, unit, product, supplier, price)
	
	def product_supplier(self, quantity, unit, product, price_per_unit, price, rounded=0):
		if rounded:
			self.out += '%g %s %s (à %.2f€): ≈%.2f€%s\n' % (quantity, unit, product, price_per_unit, price, '↓' if rounded < 0 else '↑')
		else:
			self.out += '%g %s %s (à %.2f€): %.2f€\n' % (quantity, unit, product, price_per_unit, price)


class Mux(object):
	def __init__(self, *objects):
		self.objects = objects
		
		def makef(attr):
			def f(*args):
				results = []
				for obj in objects:
					result = getattr(obj, attr)(*args)
					if not result is None:
						results.append(result)
				if len(results) == 1:
					return results[0]
				elif len(results) > 1:
					return Mux(*results)
				
			return f
		
		for obj in objects:
			for attr in dir(obj):
				if attr.startswith('__'):
					continue
				
				if hasattr(self, attr):
					continue
				
				if hasattr(getattr(obj, attr), '__call__'):
					setattr(self, attr, makef(attr))
	
	
	def __enter__(self):
		for obj in self.objects:
			if hasattr(obj, '__enter__'):
				obj.__enter__()
		
		return self
	
	
	def __exit__(self, *exc_info):
		for obj in self.objects:
			if hasattr(obj, '__exit__'):
				obj.__exit__(*exc_info)


def format_output(fmt):
	with fmt:
		# nach Kunde
		fmt.heading("Nach Kunden")
		with fmt.list():
			for customer in customers:
				tuples = list(select_tuples(orders, 2, customer))
				if len(tuples) == 0:
					continue
				
				total = sum(map(lambda x: x[tuple_indices['price_per_unit']] * x[tuple_indices['quantity']], tuples))
				(total, rounded) = cents_to_euros(total)
				
				with fmt.customer(customer, total, rounded):
					for t in tuples:
						t = decode_tuple(t)
						(price, rounded) = cents_to_euros(t['price_per_unit'] * t['quantity'])
						fmt.product_customer(t['quantity'], t['unit'], t['product'], t['supplier'], price, rounded)


		# nach Hof
		fmt.heading("Nach Lieferanten")
		with fmt.list():
			for supplier in suppliers:
				tuples = list(select_tuples(orders, tuple_indices['supplier'], supplier))
				if len(tuples) == 0:
					continue

				total = sum(map(lambda x: x[tuple_indices['price_per_unit']] * x[tuple_indices['quantity']], tuples))
				(total, rounded) = cents_to_euros(total)
				
				with fmt.supplier(supplier, total, rounded):
					for product in products:
						product_tuples = list(select_tuples(tuples, tuple_indices['product'], product))
						if len(product_tuples) == 0:
							continue
						
						quantity = sum(map(lambda x: x[tuple_indices['quantity']], product_tuples))
						price = sum(map(lambda x: x[tuple_indices['price_per_unit']] * x[tuple_indices['quantity']], product_tuples))
						unit = product_tuples[0][tuple_indices['unit']]
						price_per_unit = product_tuples[0][tuple_indices['price_per_unit']]
						
						(price, rounded) = cents_to_euros(price)
						price_per_unit = price_per_unit / 100.0
						
						fmt.product_supplier(quantity, unit, product, price_per_unit, price, rounded)


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
	if args.mail:
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
