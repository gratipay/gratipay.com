"""Generates SRI hashes of all assets.
"""
import os
import base64
import hashlib

rootDir = '.'


# Based on:
# 	https://tenzer.dk/generating-subresource-integrity-checksums/
# 	http://www.ethanjoachimeldridge.info/tech-blog/implementing-subresource-integrity-sri
def checksum(fname):
        hash = hashlib.sha384() # Use SHA-384 hash function.
        for (dirName, subdirList, fileList) in os.walk(rootDir):
                for fname in fileList:
                        if fname.endsWith(('.css', '.js')): # Look for CSS & JS files.
                                with open(fname, 'rb') as f:
                                        while True:
                                                block = f.read(2**10)
                                                if not block: break
                                                hash.update(block).digest()
                                                hash_base64 = base64.b64encode(hash).decode()
                                                digest = 'sha384-{}'.format(hash_base64)
                                        return {'sri_digest': digest}
