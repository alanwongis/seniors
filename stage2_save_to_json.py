from __future__ import print_function

import json
import pprint
import logging
import re

import BeautifulSoup # needs to be version 3


"""
(This file handles stage 2 of 3 of the conversion of the BC Seniors pdf.)

Reads the html pages, searches for fields and data values, and saves it
to a .json file

"""


# set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# create a file handler
handler = logging.FileHandler('info.log')
handler.setLevel(logging.DEBUG)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

logger.debug("test")



# GLOBALS
#---------
homes = []      # processed homes
page_num = 17   # page being processed



def _clean_string(st):
    # get rid of the following from extracted values
    return st.replace("\n", "").replace("&amp;", "and").replace("  ", " ").strip()


def to_string(div):
    # convert all the spans in a div to text
    st = ""
    for span in div.findAll("span"):
        st = st + span.string
    return _clean_string(st)
        

def parse_css(css_st):
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
        

def remove_key(dic, key):
    try:
        dic.pop(key)
    except:
        pass


def merge_keys(dic, key1, key2):
    """ merges a [key2] into [key1] and deletes [key2]""" 
    try:
        dic[key1] = dic[key2]
        dic.pop(key2)
    except:
        pass


def are_overlapping(box1, box2):
    """ checks if bounding box tuples of (left, top, width, height) intersect"""
    x1_min, y1_min, width, height = box1
    x1_max = x1_min + width
    y1_max = y1_min + height

    x2_min, y2_min, width, height = box2
    x2_max = x2_min + width
    y2_max = y2_min + height

    if x1_max < x2_min:
        return False
    if x1_min > x2_max:
        return False
    if y1_max < y2_min:
        return False
    if y1_min > y2_max:
        return False

    return True


def merge_divs(decoded_div_a, decoded_div_b):   
    top_a = decoded_div_a[1]
    top_b = decoded_div_b[1]
    if top_b < top_a: # order the contents from top to bottom
        decoded_div_a, decoded_div_b = decoded_div_b, decoded_div_a
    new_div = (decoded_div_a[0],
               decoded_div_a[1],
               decoded_div_a[2] + " " + decoded_div_b[2],
               decoded_div_a[3],
               decoded_div_a[4] )
    return new_div


def merge_overlaps(decoded_divs): 
    """ merges overlapping divs in a list"""
    overlapping = []
    sorted_divs = sorted(decoded_divs, cmp=lambda a,b: a[1]<b[1])
    i = 0
    while i<len(sorted_divs):
        div_a = sorted_divs[i]
        box_a = [div_a[0], div_a[1], div_a[3], div_a[4]]
        j = i + 1
        while j<len(sorted_divs):
            div_b = sorted_divs[j]
            box_b = [div_b[0], div_b[1], div_b[3], div_b[4]]
            if are_overlapping(box_a, box_b):
                box_a[3] = (box_b[1] + box_b[3]) - box_a[1] #merge the boundaries
                div_a[4] = box_a[3]
                sorted_divs.pop(j)
                sorted_divs.pop(i)
                sorted_divs.insert(i, merge_divs(div_a, div_b))                
            j += 1
        i += 1
    return sorted_divs


def decode_divs(divs):
    """decodes divs into a list of (left, top, text, width, height) tuples"""
    decoded = []
    for div in divs:
        style = parse_css(div["style"])
        left = style["left"]
        top = style["top"]
        width = style["width"]
        height = style["height"]
        text = to_string(div)
        decoded.append( [left, top, text, width, height] )
    return decoded


def find_sections(decoded_divs, section_headings=[]):
    """finds the tops of each given section_heading, returning sorted by position
       a list of[ (top_postion, "section name") tuples  ... ] """
    section_start = {}
    for div in decoded_divs:
        left = div[0]
        top = div[1]
        text = div[2]
        for heading in section_headings:
            if text and text.startswith(heading) and left<300:
                section_start[top] = text
    section_breaks = [ (top-10, section_start[top]) for top in sorted(section_start.keys())]
    return section_breaks
    

def make_section(decoded_divs, section_top, section_bottom):
    """filters out only the divs between section_top and section_bottom"""
    section_divs = []
    for div in decoded_divs:
        if div[1] >= section_top and div[1] < section_bottom:
            section_divs.append(div)
    return section_divs


def make_rows(decoded_divs):
    # map the vertical pixel values in use
    in_use = {}
    for div in decoded_divs:
        top = div[1]
        width = div[4]
        for i in range(top, top+width):
            in_use[i] = True
    # find line breaks by finding discontiniuties 
    y_values = sorted(in_use.iterkeys())
    line_breaks = []
    for i in range(len(y_values)-1):
        if y_values[i+1]-y_values[i] > 1:
            line_breaks.append(y_values[i]+1)
    # separate the divs into rows
    num_breaks = len(line_breaks)
    rows = [ []  for i in range(num_breaks+1) ]
    for div in decoded_divs:
        top = div[1]
        i = 0
        while i<num_breaks and top > line_breaks[i]:
            i += 1
        rows[i].append(div)
    # sort each row from left to right
    for i in range(len(rows)):
        rows[i] = sorted(rows[i])
        
    return [ [ div[2] for div in row] for row in rows ]
        
            
def make_columns(decoded_divs, column_boundaries):
    """creates a list of columns from the given divs and a list of
    (left, right) boundaries"""
    columns = [ [] for i in range(len(column_boundaries)) ]
    unmatched = []
    for div in decoded_divs:
        for n, bounds in enumerate(column_boundaries):
            matched = False
            left = bounds[0]
            right = bounds[1]
            if div[0]>= left and div[0] <= right:
                columns[n].append(div)
                matched  = True
        if not matched:
 #           logger.debug("can't match "+str(div)+" on page "+str(page_num))
            pass
    return columns


def find_closest_match(top, column_list_divs):
    # returns the value in the column list that is closest in top value
    match_value = None
    match_tolerance = 100000
    for curr_div in column_list_divs:
        curr_top = curr_div[1]
        value = curr_div[2]
        new_tolerance = abs(top-curr_top)
        if new_tolerance < match_tolerance:
            match_value = value
            match_tolerance = new_tolerance
    return match_value, match_tolerance


def match_column_values(key_column_divs, value_column_divs):
    matched_pairs = {}
    for div in key_column_divs:
        left = div[0]
        top = div[1]
        text = div[2]
        best_match, tolerance = find_closest_match(top, value_column_divs)
        if tolerance <15:
            matched_pairs[text] = best_match
        else:
            matched_pairs[text] = ""
    return matched_pairs

            
def process_page_one(page, home_values):
    
    divs = page.findAll("div")
    decoded_divs = decode_divs(divs) # change the divs into (left, top, text) tuples

    section1_start = None
    section2_start = None
    section3_start = None
    section3_end = None
    for div in decoded_divs:
        top = div[1]
        text = div[2]
        # find the sections..
        if text and text.startswith("Facility"):
            section1_start = top-10
        if text and text.startswith("Funding"):
            section2_start = top
        if text and text.startswith("Beds and"):
            section3_start = top
        if text.startswith("Source"):
            section3_end = top-10

    # Process each section...

    # FACILITY
    # --------
    facility_divs = make_section(decoded_divs, section1_start, section2_start)
    left_side = []
    right_side = []
    for div in facility_divs:
        if div[0]<306:
            left_side.append(div)
        else:
            right_side.append(div)
            
    left_rows = make_rows(left_side)
    right_rows = make_rows(right_side)

    for row in left_rows:
        home_values[row[0]] = row[1]
    for row in right_rows:
        home_values[row[0]] = row[1]
     
    
    # FUNDING
    # -------
    funding_divs = make_section(decoded_divs, section2_start, section3_start)
    funding_columns = make_columns(funding_divs,
                                   [(35, 39),
                                    (528, 534)])

    home_values.update(match_column_values(funding_columns[0], funding_columns[1]))

    # BEDS
    # ----
    bed_divs = make_section(decoded_divs, section3_start, section3_end)
    rows = make_rows(bed_divs)
    if rows[-1][0].startswith("Source"):
        rows = rows[:-1]
    for row in rows[2:]:
        home_values["Beds-"+row[0]] = row[1]
        if len(row)==4:
            home_values["Beds-"+row[2]] = row[3]

    ### clean up typos  and special values
    
    # special handling for the Parking values because field names and their values
    # don't get separated properly

    if "Visitor parking (cost) N/A" in home_values.keys():
        home_values.pop("Visitor parking (cost) N/A")
        home_values["Visitor parking (cost)"] = "N/A"
        
    if "Visitor parking (cost) No (fee charged)" in home_values.keys():
        home_values.pop("Visitor parking (cost) No (fee charged)")
        home_values["Visitor parking (cost)"] = "No (fee charged)"
        
    if "Visitor parking cost Reduced rate" in home_values.keys():
        home_values.pop("Visitor parking (cost) Reduced rate")
        home_values["Visitor parking (cost)"] = "Reduced rate"
        
    if "Visitor parking (cost) Yes (no fee)" in home_values.keys():
        home_values.pop("Visitor parking (cost) Yes (no fee)")
        home_values["Visitor parking (cost)"] = "Yes (no fee)"
        
    if "Visitor parking (cost) Yes (fee charged)" in home_values.keys():
        home_values.pop("Visitor parking (cost) Yes (fee charged)")
        home_values["Visitor parking (cost)"] = "Yes (fee charged)"

    # handle Funded Allied Health hours keys typo
    merge_keys(home_values, "Funded Allied Health hours per resident per day*",
               "Funded Allied Health hours per resident per day *")

    # handle "Reasons for Inspection" typo
    merge_keys(home_values, "Reason for Inspection","Reason for inspection")

    # handle a typo on page 359 where the Facility field and value is glitched
    if page_num == 359:
        home_values.pop("FacilityFacility")
        home_values["Facility"] = "Normanna"
        
    # remove extraneous values
    for key in ["", "Beds", "Beds*", "Beds and Rooms", "Room Configuration",
                "Source: Health Authority", "Funding"]:
        remove_key(home_values, key)       
        
        

def process_page_two(page, home_values):
    # page 2 has some issues where text fields are too close together and
    # pdf2txt.py doesn't split them on the correct boundaries. So we need
    # look for those special cases and fix them..

    divs = page.findAll("div")
    decoded_divs = decode_divs(divs) # change divs to (left, top, text, width, height) tuples
    decoded_divs = merge_overlaps(decoded_divs)    # merge any overlapping text boxes
    
    section_breaks = find_sections(decoded_divs, ["Licensing", "Complaints",
                                                  "Incidents", "Care Services",
                                                  "Facility Fees", "Inspection",
                                                  "Link to"])
    # partition the text boxes into sections
    section_divs = {}
    for top, name in section_breaks:
        section_divs[name] = []
    
    for div in decoded_divs:
        top = div[1]
        for i in range(len(section_breaks) -1):
            top = div[1]
            if top >= section_breaks[i][0] and top < section_breaks[i+1][0]:
                section_divs[section_breaks[i][1]].append(div)

    # iterate through the each section
    for section_name in section_divs.keys():
        section_rows = make_rows(section_divs[section_name])

        # INSPECTION
        #-----------
        if section_name.startswith("Inspection"):
            # fixes the date field that sometimes doesn't get separated from
            # the next field
            values  = section_rows[1]
            if values[1].find("Reason for")>0:
                split = values[1].find("Reason for")
                col_a = values[1][:split].strip()
                col_b = values[1][split:].strip()
                values[1] = col_a
                values.insert(2, col_b)
            home_values[values[0]] = values[1]
            home_values[values[2]] = values[3]

        # LICENSING
        #----------
        elif section_name.startswith("Licensing"):
            # fixes the date field that sometimes doesn't get separated from
            # the next field
            values  = section_rows[1]
            if values[1].find("Reason for")>0:
                split = values[1].find("Reason for")
                col_a = values[1][:split].strip()
                col_b = values[1][split:].strip()
                values[1] = col_a
                values.insert(2, col_b)
                
            home_values[values[0]] = values[1]
            home_values[values[2]] = values[3]

        # INCIDENTS
        #----------
        elif section_name.startswith("Incidents"):
            if section_rows[-1][0].startswith("Source"):
                section_rows = section_rows[:-1]
            if len(section_rows[1]) == 2: # two columns
                for row in section_rows[1:]:
                    kind = row[0]
                    home_values["Incidents-%s(%s)"% (kind, "Total")] = row[1]           
            elif len(section_rows[1]) == 6: # six columns SPECIAL CASE for suppressed/not available data
                for row in section_rows[1:]:
                    kind_a = row[0]
                    home_values["Incidents-%s(Total Number)"%(kind_a,)] =  row[1]
                    home_values["Incidents-%s(Per 100 beds)"%(kind_a,)] =  row[1]
                    home_values["Incidents-%s(BC Avg / 100 beds)"%(kind_a,)] =  row[2]
                    kind_a = row[3]
                    home_values["Incidents-%s(Total Number)"%(kind_a,)] =  row[4]
                    home_values["Incidents-%s(Per 100 beds)"%(kind_a,)] =  row[4]
                    home_values["Incidents-%s(BC Avg / 100 beds)"%(kind_a,)] =  row[5]
                    logger.debug("Incident special case on page:"+str(page_num+1))
            elif len(section_rows[1]) == 8: # 8 columns
                sub_headings_a = section_rows[0][2:5]
                sub_headings_b = section_rows[0][5:]
                if len(section_rows) == 1:
                    end_row = -2
                else:
                    end_row = -1
                for row in section_rows[1:end_row]:
                    kind_a = row[0]
                    kind_b = row[4]
                    for i in range(3):
                        home_values["Incidents-%s(%s)"%(kind_a, sub_headings_a[i])] = row[i+1]
                        home_values["Incidents-%s(%s)"%(kind_b, sub_headings_b[i])] = row[i+5]
            else:
                logger.debug("unknown section size on page "+str(page_num))
          

        # COMPLAINTS
        #-----------
        elif section_name.startswith("Complaints"):
        
            #  two columns per row
            if section_rows[-1][0].startswith("Source"):
                section_rows = section_rows[:-1]
            for row in section_rows[1:]: # skip the header
                home_values["Complaints-"+row[0]] = row[1]
                home_values["Complaints-"+row[2]] = row[3]
                

        # FACILITY FEES
        #--------------
        elif section_name.startswith("Facility Fees"):
            
            #  two columns per row
            if section_rows[-1][0].startswith("Source"):
                section_rows = section_rows[:-1]
            if len(section_rows[-1]) == 3:
                section_rows[-1].append(" ") # handle Other Fees which has no value
            for row in section_rows[2:]: # skip the title and the headers
                home_values["Service Included-"+row[0]] = row[1]
                home_values["Service Included-"+row[2]] = row[3]
                

        # CARE SERVICES
        #--------------
        elif section_name.startswith("Care Services"):
            #  6 columns per row
            if section_rows[-1][0].startswith("Source"):
                section_rows = section_rows[:-1]
            for row in section_rows[1:]: # skip the headers
                home_values["Care Quality(Facility)-"+row[0]] = row[1]
                home_values["Care Quality(BC Avg)-"+row[0]]  =  row[2]
                


        elif section_name.startswith("Link to"):
            #
            pass
        else:
            print("Can't recognize section", section_name) 
            
        # ** fixes for typos and errors **
        
        # handle "Reasons for Inspection" similar values
        merge_keys(home_values, "Service Included-Other fees", "Service Included-Other Fees")
                
    return
              
        
       
def main():
    global homes
    global page_num
    
    print("reading pages...")
    page_num= 17
    while page_num < 600:
        
        curr_home = {}
        
        print("page  " +str(page_num))
        page_one = BeautifulSoup.BeautifulSoup(open("page%03i.html"%page_num))
        #  ** special case fix for page 329, a typo for the 'Beds and Rooms' **
        if page_num == 329:
            bad_span = page_one.find(text=re.compile("951"))
            bad_span.string.replaceWith("Beds and Rooms")
            
        process_page_one(page_one, curr_home)
            
        print("page  " + str(page_num+1))
        page_two = BeautifulSoup.BeautifulSoup(open("page%03i.html"%(page_num+1)))
        # ** special case fixes for page 98 and 190, these pages have a blank
        # space rather than a value of 'N/A" in the field. We "fix" this by injecting
        # a value into the parsed page because it's cleaner that putting a
        # special case check in the processing code
        if page_num+1 == 98:
            new_div  = BeautifulSoup.Tag(page_two, "div")
            new_div["style"] = "top: 228px; left:481px; height:10px; width:10px;"
            new_span = BeautifulSoup.Tag(page_two, "span")
            new_span.insert(0, BeautifulSoup.NavigableString("N/A"))
            new_div.insert(0, new_span)
            page_two.html.body.insert(0,new_div)
        elif page_num+1 == 190:
            new_div  = BeautifulSoup.Tag(page_two, "div")
            new_div["style"] = "top: 232px; left:481px; height:10px; width:10px;"
            new_span = BeautifulSoup.Tag(page_two, "span")
            new_span.insert(0, BeautifulSoup.NavigableString("N/A"))
            new_div.insert(0, new_span)
            page_two.html.body.insert(0,new_div)
        elif page_num+1 == 350:
            new_div  = BeautifulSoup.Tag(page_two, "div")
            new_div["style"] = "top: 111px; left:249px; height:10px; width:10px;"
            new_span = BeautifulSoup.Tag(page_two, "span")
            new_span.insert(0, BeautifulSoup.NavigableString("N/A"))
            new_div.insert(0, new_span)
            page_two.html.body.insert(0,new_div)
            new_div  = BeautifulSoup.Tag(page_two, "div")
            new_div["style"] = "top: 111px; left:518px; height:10px; width:10px;"
            new_span = BeautifulSoup.Tag(page_two, "span")
            new_span.insert(0, BeautifulSoup.NavigableString("N/A"))
            new_div.insert(0, new_span)
            page_two.html.body.insert(0,new_div)
        
        process_page_two(page_two, curr_home)

        homes.append(curr_home)
        page_num += 2

    # save as a json file
    print("writing...")
    outfile = open("homes.json", "w")
    outfile.write(json.dumps(homes, indent=4, sort_keys=True,))
    outfile.close()


    
if __name__ == "__main__":
    main()
    
