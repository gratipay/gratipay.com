from setuptools import setup, find_packages

from gratipay.version import get_version


setup( name='gratipay'
     , version=get_version()
     , packages=find_packages()
     , entry_points = { 'console_scripts'
                      : [ 'payday=gratipay.cli:payday'
                        , 'fake_data=gratipay.utils.fake_data:main'
                        , 'sync-npm=gratipay.sync_npm.cli:main'
                        , 'queue-branch-email=gratipay.utils.emails.queue_branch_email:main'
                        , 'dequeue-emails=gratipay.utils.emails.dequeue_emails:main'
                        , 'list-email-queue=gratipay.utils.emails.list_email_queue:main'
                         ]
                       }
      )
