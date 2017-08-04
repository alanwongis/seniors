""" Stage 3 of 3 of Seniors directory conversion.

Run this file to convert the .json file created by the previous stage into a
.csv file

"""



import json
import csv, codecs, cStringIO

class UnicodeWriter:
    def __init__(self, f, dialect=csv.excel, encoding="utf-8-sig", **kwds):
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()
    def writerow(self, row):
        '''writerow(unicode) -> None
        This function takes a Unicode string and encodes it to the output.
        '''
        self.writer.writerow([s.encode("utf-8") for s in row])
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        data = self.encoder.encode(data)
        self.stream.write(data)
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


data = json.loads(open("homes.json","r").read())



keys = set()
for home in data:
    for key in home.keys():
        keys.add(key)


key_list = list(keys)
key_list.sort()
for k in key_list:
    print k



writer = UnicodeWriter(open("homes.csv", "w"))

writer.writerow(key_list)

for n,home in enumerate(data):
    writer.writerow([home.get(k, "") for k in key_list])


    
