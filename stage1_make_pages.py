"""

(Stage 1 of 3 of the conversion of the Seniors directory pdf)

First an html file is generated from the pdf with the following command:
"pdf2txt.py -o text.html -A  -Y loose -t html -L 0.4 -M 1.1 directory.pdf"

(Note- you must have the pdf2txt library and utilities installed. It can be
      found here: http://www.unixuser.org/~euske/python/pdfminer/)

Then run this script to split the resulting single html file into individual
pages.

"""

import BeautifulSoup as bs



def find_top(elem):
    style = elem["style"]
    start = style.find("top:")
    end = style[start:].find("px")
    return int(style[start+4:start+end])

def shift_top(elem, amt):
    style = elem["style"]
    start = style.find("top:")
    end = style[start:].find("px")
    curr_top = int(style[start+4:start+end])
    new_top = curr_top-amt
    new_style = style[:start]+"top:"+str(new_top)+style[start+end:]+" background-color: pink;"
    elem["style"] = new_style

tops = []


print "reading..."
soup = bs.BeautifulSoup(open("text.html"))
divs = soup.findAll("div")

print "splitting into pages"
#split into pages
pages = []

page = []

for div in divs:
    if div.a:
        pages.append(page)
        page = []
    else:
        page.append(div)
if len(page)>0:
    pages.append(page)

# remove the divs that draw the formatting boxes
for page in pages:
    for div in page:
        if len(div.findAll("span"))>10:
            page.remove(div)
        
# remove all the <br \> tags
for page in pages:
    for div in page:
        brs = div.findAll("br")
        if brs:
            for br in brs:
                br.extract()

            
# write each page
for n,page in enumerate(pages):
    filename = "page%03i.html" % n
    outfile = open(filename, "w")
    outfile.write("<html><head><title>%s</title></head><body>"%filename)

    #reset the top of each page
    tops = [10000000, ]
    for div in page:
        tops.append(find_top(div))
    min_top = min(tops)
    for div in page:
        shift_top(div, min_top)
        
    # sort divs by vertical position
    tmp = []
    for div in page:
        tmp.append( (find_top(div), div) )
    tmp.sort()
    sorted_divs = [ x[1] for x in tmp ]
    
    for div in sorted_divs:
        
        outfile.write(str(div))
    outfile.write("</body></html>")
    outfile.close()
    
