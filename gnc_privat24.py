#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

import gnucash
from lxml import objectify
import argparse
from getpass import getpass
from time import strptime
from datetime import datetime
import dateutil.parser
import dateutil.rrule
from requests import session, post  # FIXME: check version. keep-alive works only in 0.14.x and later
from requests.auth import HTTPBasicAuth
from time import sleep

APP_NAME = 'gnc_privat24.py'

try:
	import gnomekeyring

	# If password is already in gnome-keyring than use it.
	# Else ask user and save to keyring.
	def get_passwd(address, username):
		kr = gnomekeyring.get_default_keyring_sync()
		attr = {
			'username': username,
			'address': address,
			'application': APP_NAME
		}
		try:
			result_list = gnomekeyring.find_items_sync(gnomekeyring.ITEM_GENERIC_SECRET, attr)
		except gnomekeyring.NoMatchError:
			passwd = getpass('Password: ')
			gnomekeyring.item_create_sync(kr, gnomekeyring.ITEM_GENERIC_SECRET, address, attr, passwd, True)
			return passwd

		passwds = [result.secret for result in result_list]
		if len(passwds) > 1:
			raise Exception('More than one password')
		return passwds[0]

except ImportError:

	def get_passwd(address, username):
		return getpass('Password: ')


class GncPrivat24Session(gnucash.Session):
	"""
	Import transactions from 'statements' object
	which is parsed by lxml.objectify from Privat24 statements XML
	"""
	def ImportPrivat24Statements(self, statements):
		book = self.book
		comm_table = book.get_table()
		root = book.get_root_account()

		for r in statements.iterchildren():
			tr_duplicate = False
			ccy = comm_table.lookup('CURRENCY', r.amount.attrib['ccy'])
			trans = gnucash.Transaction(book)
			trans.BeginEdit()
			trans.SetNum(r.info.attrib['ref'])
			trans.SetDescription(r.purpose.text.encode('UTF-8'))
			trans.SetCurrency(ccy)
			t = strptime(r.info.attrib['postdate'], "%Y%m%dT%H:%M:%S")
			trans.SetDate(t.tm_mday, t.tm_mon, t.tm_year)
			amt = gnucash.GncNumeric(float(r.amount.attrib['amt']) * 100, 100)

			for i in [r.debet, r.credit]:
				acc = root.lookup_by_code(i.account.attrib['number'])
				if acc is None:
					acc = gnucash.Account(book)
					acc.SetCommodity(ccy)
					# TODO: Choose type based on transaction properties
					acc.SetType(gnucash.ACCT_TYPE_EXPENSE)
					acc.SetCode(i.account.attrib['number'])
					acc.SetName(i.account.attrib['name'].encode('UTF-8'))
					root.append_child(acc)

				# check if transaction already exists
				# TODO: use QofQuery when it's available
				acc_splits = acc.GetSplitList()
				for s in acc_splits:
					if s.GetParent().GetNum() == r.info.attrib['ref']:
						if not tr_duplicate:
							print "duplicate: %s" % r.purpose.text.encode('UTF-8')
						tr_duplicate = True

				split = gnucash.Split(book)
				split.SetParent(trans)
				split.SetValue(amt if i.tag[0].upper() == r.info.attrib['shorttype'] else amt.neg())
				split.SetAccount(acc)

			if tr_duplicate:
				trans.RollbackEdit()
			else:
				trans.CommitEdit()

			# sleep for 2 seconds po prevent GnuCash backup copies creation errors
			print 'sleeping...'
			sleep(2)

		self.save()

#==========================================================================

if __name__ == "__main__":

	URL_RESTS = 'https://client-bank.privatbank.ua/p24/c2brest'
	URL_STATEMENTS = 'https://client-bank.privatbank.ua/p24/c2bstatements'

	def parse_date(datestr):
		try:
			return dateutil.parser.parse(datestr, dayfirst=True)
		except ValueError as e:
			return datetime.now()

	ap = argparse.ArgumentParser(description='Imports Privat24 statements into Gnucash book')
	ap.add_argument('book', help='Gnucash book to import data to')
	ap.add_argument('-l', '--login', required=True, help='login name in Privat24')
	ap.add_argument('-a', '--account', required=True, help='account number in Privat24')
	ap.add_argument('-s', '--start', required=True, type=parse_date, help='start of imported period')
	ap.add_argument('-e', '--end', type=parse_date, default="", help='end of imported period')
	args = ap.parse_args()

	# pass credentials only with the first request of session
	data_rest = {
		'PUREXML': 'true',
	}

	pr24_session = session()
	pr24_session.auth = HTTPBasicAuth(args.login, get_passwd(URL_RESTS, args.login))
	# TODO: catch exception
	req_rest = pr24_session.post(URL_RESTS, data_rest, verify=True)
	req_rest.raise_for_status()

	try:
		gnc_session = GncPrivat24Session(args.book)
		for dt in dateutil.rrule.rrule(dateutil.rrule.MONTHLY, dtstart=args.start, until=args.end):
			data_statements = {
				'PUREXML': 'true',
				'acc': args.account,
				#'type_contractor': 'EGRPU',
				#'rcrf': '1234567',
				'year': dt.year,
				'month': dt.month,
			}
			print data_statements
			# TODO: catch exception
			req_statements = pr24_session.post(URL_STATEMENTS, data_statements, verify=True)
			req_statements.raise_for_status()
			statements = objectify.fromstring(req_statements.content).list
			#statements = objectify.parse('statements.xml').getroot().list
			gnc_session.ImportPrivat24Statements(statements)

	except gnucash.gnucash_core.GnuCashBackendException, e:
		print e.message
	finally:
		gnc_session.end()
