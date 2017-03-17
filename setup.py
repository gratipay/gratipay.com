from setuptools import setup, find_packages

from gratipay.version import get_version


setup( name='gratipay'
     , version=get_version()
     , packages=find_packages()
     , entry_points = { 'console_scripts'
                      : [             'payday=gratipay.cli.payday:main'
                        ,          'fake-data=gratipay.cli.fake_data:main'
                        ,           'sync-npm=gratipay.cli.sync_npm:main'
                        , 'queue-branch-email=gratipay.cli.queue_branch_email:main'
                        ,     'dequeue-emails=gratipay.cli.dequeue_emails:main'
                        ,   'list-email-queue=gratipay.cli.list_email_queue:main'
                         ]
                       }
      )
