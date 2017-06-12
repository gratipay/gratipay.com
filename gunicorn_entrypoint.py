from aspen import log
from gratipay.application import Application
log('Instantiating Application from gunicorn_entrypoint')
website = Application().website
