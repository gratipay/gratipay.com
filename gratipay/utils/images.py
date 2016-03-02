import zipfile
from cStringIO import StringIO

import requests

def imgize(image, image_type):
    large = None
    small = None
    crops = requests.post( 'http://gip.rocks/v1',
                           data=image,
                           headers={'Content-Type': image_type}
            )
    if crops.status_code == 200:
        zf = zipfile.ZipFile(StringIO(crops.content))
        large = zf.open('160').read()
        small = zf.open('48').read()

    return crops.status_code, large, small