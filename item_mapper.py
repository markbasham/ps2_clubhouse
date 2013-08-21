'''
Created on 21 Aug 2013

@author: ssg37927
'''

import urllib2

for i in range(100):
    print "Getting icon %i" % i
    try:
        data = urllib2.urlopen('https://census.soe.com/s:soe/img/ps2/icon/%i/item' % (i)).read()
        f = open('c:/pics/%06i.png'%i,'wb')
        f.write(data)
        f.close()
    except Exception as e :
        print "    Failed to process"
