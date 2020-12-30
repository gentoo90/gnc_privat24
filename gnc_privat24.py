#!/usr/bin/env python3
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

from typing import List
import gnucash
import argparse
from time import strptime
from getpass import getpass
from datetime import datetime
import dateutil.parser
import dateutil.rrule
from requests import session
from privat24_api import parse_pr24_statements, Transaction
from gnc_privat24_session import GncPrivat24Session
import keyring

APP_NAME = 'gnc_privat24.py'

def get_passwd(address, username, prompt):
    passwd = keyring.get_password(address, username)
    if passwd is None:
        passwd = input(f'{prompt}: ')
        keyring.set_password(address, username, passwd)
    return passwd

# def get_passwd(address, username):
#     return getpass('Password: ')

# ==========================================================================


if __name__ == "__main__":

    URL_TRANSACTIONS = 'https://acp.privatbank.ua/api/proxy/transactions'
    STRFTIME = '%d-%m-%Y'

    def parse_date(datestr):
        try:
            return dateutil.parser.parse(datestr, dayfirst=True)
        except ValueError as e:
            return datetime.now()

    ap = argparse.ArgumentParser(
        description='Imports Privat24 statements into Gnucash book')
    ap.add_argument('book', help='Gnucash book to import data to')
    ap.add_argument('-l', '--login', required=True,
                    help='login name in Privat24')
    ap.add_argument('-a', '--account', required=True,
                    help='account number in Privat24')
    ap.add_argument('-s', '--start', required=True,
                    type=parse_date, help='start of imported period')
    ap.add_argument('-e', '--end', type=parse_date,
                    default="", help='end of imported period')
    ap.add_argument('-f', '--file',
                    help='path to file to save transactions to (JSON)')
    args = ap.parse_args()

    pr24_session = session()
    pr24_session.headers.update({
        'Content-Type': 'application/json;charset=utf8',
        'id': get_passwd(f'{APP_NAME} ID', args.login, 'Enter Autoclient ID'),
        'token': get_passwd(f'{APP_NAME} Token', args.login, 'Enter Autoclient Token')
    })

    try:
        gnc_session = GncPrivat24Session(args.book)
        # for dt in dateutil.rrule.rrule(dateutil.rrule.MONTHLY, dtstart=args.start, until=args.end):
        params_transactions = {
            'acc': args.account,
            'startDate': args.start.strftime(STRFTIME),
            'endDate': args.end.strftime(STRFTIME)
        }
        req_transactions = pr24_session.post(
            URL_TRANSACTIONS, params=params_transactions, verify=True)
        req_transactions.raise_for_status()

        if args.file is not None:
            with open(args.file, 'wb') as f:
                f.write(req_transactions.content)

        resp = parse_pr24_statements(req_transactions.text)
        statements = resp['StatementsResponse']['statements']
        transactions: List[Transaction] = [tr for st in statements for tr in st.transactions.values()]
        transactions.sort(key=lambda tr: strptime(tr.DATE_TIME_DAT_OD_TIM_P, "%d.%m.%Y %H:%M:%S"))
        gnc_session.ImportPrivat24Statements(transactions)

    except gnucash.gnucash_core.GnuCashBackendException as e:
        print(e)
    finally:
        gnc_session.end()
