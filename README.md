# Gnucash Privat24 (Приват24) statements importer #

This script imports statements from [Privatbank (Приватбанк)](https://privatbank.ua/) client-bank into [Gnucash](https://www.gnucash.org/) book.
Privatbank Autoclient API is described [here](https://docs.google.com/document/d/e/2PACX-1vTtKvGa3P4E-lDqLg3bHRF6Wi9S7GIjSMFEFxII5qQZBGxuTXs25hQNiUU1hMZQhOyx6BNvIZ1bVKSr/pub).

Response fields mapped to gnucash fields:
 * `BPL_REF + '.' + BPL_REFN` - Transaction number
 * `DATE_TIME_DAT_OD_TIM_P` - Transaction date
 * `BPL_OSND` - Transaction description
 * `BPL_SUM` - Transaction value
 * `AUT_MY_ACC` and `AUT_CNTR_ACC` - Account codes (if account with the given code doen't exist it will be created under the root account with `AUT_MY_NAM` or `AUT_CNTR_NAM` as its name respectively)

## Usage ##

You need to enable Autoclient in your account as described [here](https://docs.google.com/document/d/e/2PACX-1vTion-fu1RzMCQgZXOYKKWAmvi-QAAxZ7AKnAZESGY5lF2j3nX61RBsa5kXzpu7t5gacl6TgztonrIE/pub).

```bash
$ gnc_privat24 --login <login in Privat24> --account <account number> --start <dd.mm.yyyy> [--end <dd.mm.yyyy>] <book.gnucash>
```
On the first run this will ask for autoclients `id` and `token` and store them in the keyring.

## Dependencies ##

 * [Python](https://www.python.org/) >= 3.6
 * [Gnucash](https://www.gnucash.org/) with Python bindings (tested with 4.2)
 * [python-dateutil](https://pypi.python.org/pypi/python-dateutil)
 * [requests](https://pypi.python.org/pypi/requests)
 * [keyring](https://github.com/jaraco/keyring)
 * [schwifty](https://github.com/mdomke/schwifty)

On Gentoo Linux you can install all of this by running:
```bash
$ sudo emerge -av app-office/gnucash dev-python/python-dateutil dev-python/requests dev-python/keyring
$ pip install --user schwifty
```
