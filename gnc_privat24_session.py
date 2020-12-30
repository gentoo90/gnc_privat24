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

from time import strptime, sleep
from typing import List
import gnucash
from privat24_api import Transaction
from schwifty import IBAN


class DuplicateTransactionError(Exception):
    pass

class InvalidTransactionType(Exception):
    pass


class GncPrivat24Session(gnucash.Session):
    """
    Import transactions from 'statements' object
    which is parsed by lxml.objectify from Privat24 statements XML
    """

    def __init__(self, book_path: str):
        super(GncPrivat24Session, self).__init__(book_path)
        self.comm_table = self.book.get_table()
        self.root = self.book.get_root_account()

    def GetAccount(self, acc_number: IBAN) -> gnucash.Account:
        acc = self.root.lookup_by_code(str(acc_number))
        if acc is None:
            acc = self.root.lookup_by_code(
                acc_number.account_code.lstrip('0'))
            print(f'WARNING: OLD ACCOUNT NUMBER FORMAT - {acc}')
        return acc

    def GetOrCreateAccount(self, acc_number: IBAN, acc_name: str, ccy: gnucash.GncCommodity) -> gnucash.Account:
        acc = self.GetAccount(acc_number)
        if acc is None:
            acc = gnucash.Account(self.book)
            acc.SetCommodity(ccy)
            # TODO: Choose type based on transaction properties
            acc.SetType(gnucash.ACCT_TYPE_EXPENSE)
            acc.SetCode(str(acc_number))
            acc.SetName(acc_name)
            self.root.append_child(acc)
            print(f'NEW ACCOUNT: {acc_number} - {acc_name}')

        return acc

    def AddSplitToAccount(self, tran: gnucash.Transaction, acc: gnucash.Account, amt: gnucash.GncNumeric):
        # check if transaction already exists
        # TODO: use QofQuery when it's available
        acc_splits = acc.GetSplitList()
        for s in acc_splits:
            s_parent = s.GetParent()
            if s_parent.GetNum() == tran.GetNum():
                raise DuplicateTransactionError

        split = gnucash.Split(self.book)
        split.SetParent(tran)
        split.SetValue(amt)
        split.SetAccount(acc)

    def ImportPrivat24Statements(self, transactions: List[Transaction]):
        for t in transactions:
            ccy = self.comm_table.lookup('CURRENCY', t.BPL_CCY)
            trans = gnucash.Transaction(self.book)
            trans.BeginEdit()
            trans.SetNum(t.ref)
            trans.SetDescription(t.BPL_OSND)
            trans.SetCurrency(ccy)
            dt = strptime(t.DATE_TIME_DAT_OD_TIM_P, "%d.%m.%Y %H:%M:%S")
            trans.SetDate(dt.tm_mday, dt.tm_mon, dt.tm_year)
            amt = gnucash.GncNumeric(
                int(round(float(t.BPL_SUM) * 100)), 100)  # в копейках

            # deb_acc = self.GetOrCreateAccount(t.bpl_a_iban, t.BPL_A_NAM, ccy)
            # cred_acc = self.GetOrCreateAccount(t.bpl_b_iban, t.BPL_B_NAM, ccy)

            if (t.TRANTYPE == 'C'): # my account is the credit account
                deb_acc = self.GetOrCreateAccount(t.cntr_acc, t.AUT_CNTR_NAM, ccy)
                cred_acc = self.GetOrCreateAccount(t.my_acc, t.AUT_MY_NAM, ccy)
            elif (t.TRANTYPE == 'D'): # my account is the debit account
                deb_acc = self.GetOrCreateAccount(t.my_acc, t.AUT_MY_NAM, ccy)
                cred_acc = self.GetOrCreateAccount(t.cntr_acc, t.AUT_CNTR_NAM, ccy)
            else:
                raise InvalidTransactionType

            try:
                self.AddSplitToAccount(trans, deb_acc, amt.neg())
                self.AddSplitToAccount(trans, cred_acc, amt)
                trans.CommitEdit()
            except DuplicateTransactionError:
                print(f'duplicate: {t.BPL_OSND}')
                trans.RollbackEdit()

            # without this transactions have the same creation time which causes errors
            print('sleeping...')
            sleep(2)

        self.save()
