# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from aspen import log
from gratipay.application import Application


def main():
    try:
        log('Instantiating Application from gratipay.cli.payday')
        Application().payday_runner.run_payday()
    except KeyboardInterrupt:
        pass
    except:
        import aspen
        import traceback
        aspen.log(traceback.format_exc())
