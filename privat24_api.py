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

import json
from typing import Dict, Any
from schwifty import IBAN


class Transaction:
    def __init__(self, fields):
        # self.AUT_CNTR_ACC = fields['AUT_CNTR_ACC']
        self.AUT_MY_CRF = fields['AUT_MY_CRF']
        self.AUT_MY_MFO = fields['AUT_MY_MFO']
        self.AUT_MY_ACC = fields['AUT_MY_ACC']
        self.AUT_MY_NAM = fields['AUT_MY_NAM']
        self.AUT_MY_MFO_NAME = fields['AUT_MY_MFO_NAME']
        self.AUT_CNTR_CRF = fields['AUT_CNTR_CRF']
        self.AUT_CNTR_MFO = fields['AUT_CNTR_MFO']
        self.AUT_CNTR_ACC = fields['AUT_CNTR_ACC']
        self.AUT_CNTR_NAM = fields['AUT_CNTR_NAM']
        self.AUT_CNTR_MFO_NAME = fields['AUT_CNTR_MFO_NAME']
        self.BPL_CCY = fields['BPL_CCY']
        self.BPL_FL_REAL = fields['BPL_FL_REAL']
        self.BPL_FL_DC = fields['BPL_FL_DC']
        self.BPL_PR_PR = fields['BPL_PR_PR']
        self.BPL_DOC_TYP = fields['BPL_DOC_TYP']
        self.BPL_NUM_DOC = fields['BPL_NUM_DOC']
        self.BPL_DAT_KL = fields['BPL_DAT_KL']
        self.BPL_DAT_OD = fields['BPL_DAT_OD']
        self.BPL_OSND = fields['BPL_OSND']
        self.BPL_SUM = fields['BPL_SUM']
        self.BPL_SUM_E = fields['BPL_SUM_E']
        self.BPL_REF = fields['BPL_REF']
        self.BPL_REFN = fields['BPL_REFN']
        self.BPL_TIM_P = fields['BPL_TIM_P']
        self.DATE_TIME_DAT_OD_TIM_P = fields['DATE_TIME_DAT_OD_TIM_P']
        self.ID = fields['ID']
        self.TRANTYPE = fields['TRANTYPE']
        if self.TRANTYPE == 'D':
            self.BPL_DLR = fields['BPL_DLR']
        self.TECHNICAL_TRANSACTION_ID = fields['TECHNICAL_TRANSACTION_ID']

    def get_iban(self, mfo: str, acc: str) -> IBAN:
        try:
            return IBAN(acc)
        except ValueError as err:
            return IBAN.generate('UA', mfo, acc)

    # @property
    # def bpl_a_iban(self) -> IBAN:
    #     return self.get_iban(self.BPL_A_MFO, self.BPL_A_ACC)

    # @property
    # def bpl_b_iban(self) -> IBAN:
    #     return self.get_iban(self.BPL_B_MFO, self.BPL_B_ACC)

    @property
    def my_acc(self):
        return self.get_iban(self.AUT_MY_MFO, self.AUT_MY_ACC)

    @property
    def cntr_acc(self):
        return self.get_iban(self.AUT_CNTR_MFO, self.AUT_CNTR_ACC)

    @property
    def ref(self):
        return f'{self.BPL_REF}.{self.BPL_REFN}'

    def __repr__(self):
        amt = float(self.BPL_SUM)
        if self.TRANTYPE == 'D':
            amt = -amt
        return f'{self.DATE_TIME_DAT_OD_TIM_P}: {amt:>10} {self.BPL_CCY} {str(self.my_acc):>30} {self.TRANTYPE} {str(self.cntr_acc):>30} "{self.AUT_CNTR_NAM}"'


class Statement:
    def __init__(self, transactions: Dict[str, Transaction]):
        self.transactions = transactions
        '''The Transactions'''


def object_hook(dct: Dict[str, Any]):
    if 'TRANTYPE' in dct:
        tr = Transaction(dct)
        # print(tr.__repr__())
        return tr
    if all([type(t) == Transaction for t in dct.values()]):
        return Statement(dct)
    return dct


def parse_pr24_statements(s: str):
    return json.loads(s, object_hook=object_hook)
