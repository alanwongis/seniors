from __future__ import print_function

import BeautifulSoup as bs
from PIL import Image, ImageFilter


# this program analyzes all the pages to try to find the column locations

raw_lefts = {}
tops = {}

funding_left = {}
funding_top = {}

bed_left = {}
bed_top = {}


def clean_string(st):
    # get rid of the following from extracted values
    return st.replace("\n", "").replace("&amp;", "and").replace("  ", " ").strip()


def to_string(div):
    st = ""
    for span in div.findAll("span"):
        st = st + span.string
    return clean_string(st)
        


def parse_css_style(css_st):
    # create a dictionary of css params from a css formatting string
    css_values = {"top":0, "left":0}
    if css_st:
        raw_pairs = css_st.split(";")
        for pair in raw_pairs:
            pair_values = pair.strip().split(":")
            if len(pair_values) == 2:
                key, value = pair_values[0], pair_values[1]
                if value.endswith("px"):
                    value = int(value[:-2])
                css_values[key] = value
    return css_values


def inc_histogram(histogram_dict, value):
    histogram_dict.setdefault(value, 0)
    histogram_dict[value] += 1


def print_histogram(histogram_dict):
    new_dict = {}
    for k in histogram_dict.keys():
        new_dict[k] = int(histogram_dict[k])
    for n in sorted(histogram_dict.iterkeys()):
        print(n, new_dict[n])
        
        
    

section1_lefts = {}
section2_lefts = {}
section3_lefts = {}
        

for n in range(17, 600, 2):
    # scan the odd pages only
    section1_start = None
    section2_start = None
    section3_start = None
    section3_end = None
    filename = "page%03i.html" % n
    soup = bs.BeautifulSoup(open(filename,"r").read())
    divs = soup.findAll("div")
    for div in divs:
        style_params = parse_css_style(div["style"])
        text = to_string(div)
        left_value = style_params.get("left")
        top_value = style_params.get("top")
        if left_value:
            inc_histogram(raw_lefts, left_value)

        # find the sections
        if text and text.startswith("Facility"):
            section1_start = top_value-10
        if text and text.find("Funding") >=0:
            section2_start = top_value
        if text and text.find("Beds and") >=0:
            section3_start = top_value
        if text.startswith("Source: "):
            section3_end = top_value+10
            
    if section1_start and section2_start and section3_start and section3_end:
        for div in divs:
            style_params = parse_css_style(div["style"])
            text = to_string(div)
            left_value = style_params.get("left")
            top_value = style_params.get("top")
            if  top_value > section1_start and top_value < section2_start:
                inc_histogram(section1_lefts, left_value)
            elif top_value > section2_start and top_value < section3_start:
                inc_histogram(section2_lefts, left_value)
            elif top_value > section3_start and top_value < section3_end:
                inc_histogram(section3_lefts, left_value)
    else:
        print("can't find sections for page", n,
              str(section1_start),
              str(section2_start),
              str(section3_start),
              str(section3_end))
        
            


            
print("Columns:")

# create a histogram of the left columns
lefts = {}
print_histogram(lefts)


print("Section one(Facility) columns:")
print_histogram(section1_lefts)

print("Section two(Funding) columns:")
print_histogram(section2_lefts)

print("Section three(Beds) columns:")
print_histogram(section3_lefts)

def make_heatmap():

    # create a heatmap of the divs
    heatmap = [ [0 for n in range(800)] for m in range(640)]

    for n in range(17,600, 2):
        # scan the odd pages only
        filename = "page%03i.html" % n
        soup = bs.BeautifulSoup(open(filename,"r").read())
        divs = soup.findAll("div")
        for div in divs:
            style_params = parse_css_style(div["style"])
            left_value = style_params.get("left")
            top_value = style_params.get("top")
            if left_value and top_value:
                x = int(left_value[:-2])
                y = int(top_value[:-2])
                heatmap[x][y] += 1

        #print("page",n)


    for m in range(640):
        for n in range(800):
            if heatmap[m][n]>max_value:
                max_value = heatmap[m][n]

    for m in range(640):
        for n in range(800):
            heatmap[m][n] = int(heatmap[m][n]/max_value *255)


    img = Image.new("L", (640, 800))
    pixels = img.load()
    for m in range(640):
        for n in range(800):
            pixels[m,n] = heatmap[m][n]
    blurred = img
    blurred.save("heatmap1.png")


         


            
    
