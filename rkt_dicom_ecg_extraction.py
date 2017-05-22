import sys
import os
import glob
import getopt
import dicom
import PIL.Image
import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import csv
import json

from functions import createImage

if len(sys.argv) == 3:

    InputFolderPath = sys.argv[1]  # "./../Annotated images/Normal/"
    OutputFolderPath = sys.argv[2]  # "./../Annotated images/Normal/out/"
    
    for img in glob.glob(InputFolderPath+"/*.dcm"):
        ######################## 1. LOAD IMAGE ###################################
        inputpath = InputFolderPath + "/" + os.path.basename(img)
        print("Input: ", inputpath)
        outputpath = OutputFolderPath + "/" + os.path.basename(img)
        print("output:", outputpath)

        plan = dicom.read_file(inputpath)
        img = createImage(plan)

        height = plan.Rows
        width = plan.Columns

        # we obtain the Manufacturer:
        # '.rstrip()' removes final blank spaces in strings
        manufacturer = plan.Manufacturer.rstrip()

        # img.show()

        print()
        print('The manufacturer is:', manufacturer)
        ##########################################################################

        ######################### 2. OBTENTION OF THE ECG COLOR ##################
        dict_colors = {'GE Vingmed Ultrasound': (
            23, 179, 161), 'Philips Medical Systems': (69, 249, 69)}

        # ECG color of an echocardiogram from 'manufacturer'
        ecg_color = dict_colors[manufacturer]

        white = (255, 255, 255)  # rgb code
        black = (0, 0, 0)  # rgb code
        ##########################################################################

        ###################### 3.THRESHOLD, 4. MASK OBTENTION ####################
        m_img = img.copy()  # (future) masked image
        m_px = m_img.load()  # pixels of the (future) masked image

        for x in range(width):  # columns
            for y in range(height):  # rows

                # Thresholding
                if m_px[x, y] == ecg_color:
                    m_px[x, y] = white
                else:
                    m_px[x, y] = black

        # m_img.show() # masked image
        ##########################################################################

        ##################### 5. EXTRACTION OF THE DIGITAL SIGNAL (AND INTERPOLATI
        yList_json = []  # heights expressed from the TOP of the dicom
        # heights expressed from the BOTTOM of the dicom (WE OBTAIN IT LATER)
        yList_interp_csv = []
        xList = []  # x-coords
        start = 0
        x_ini = 0

        for x in range(width):  # columns
            # rows, from the bottom to the top of the image
            for y in reversed(range(height)):

                if m_px[x, y] == white:  # if we find a white pixel:
                    # we add it at 'yList_json'
                    yList_json.append(y)

                    if start == 0:  # i.e., we just entered in the ECG window
                        x_ini = x  # x-coord where the ECG starts
                        start += 1

                    # x-coords like [0,1,...], instead of [x_ini, x_ini+1,...]
                    xList.append(x - x_ini)
                    break

        # INTERPOLATION (only if necessary)
        if max(xList) > len(yList_json):

            x_values = np.arange(max(xList))
            yList_interp_json = interp1d(xList, yList_json, kind='cubic')(x_values)

            # We substitute possible negative values to 0
            if any(n < 0 for n in yList_interp_json):
                yList_interp_json = [0 if j < 0 else j for j in yList_interp_json]

            xList_interp = x_values.tolist()

        else:
            yList_interp_json = yList_json[:]
            xList_interp = xList[:]

        # OBTENTION OF THE CSV FILE
        # (height-1) is the max_y_coord
        yList_interp_csv = [(height - 1 - y) for y in yList_interp_json]
        if any(n < 0 for n in yList_interp_csv):
            yList_interp_csv = [0 if j < 0 else j for j in yList_interp_csv]

        # NORMALIZATION OF THE ECG
        max_y_csv = max(yList_interp_csv)
        max_y_json = max(yList_interp_json)

        norm_yList_interp_csv = [int((i * 100) / max_y_csv)
                                for i in yList_interp_csv]
        norm_yList_interp_json = [int((i * 100) / max_y_json)
                                for i in yList_interp_json]
        #########################################################################
        print()
        print('Outputs:')
        ######################## 6. CSV FILE CREATION ###########################
        # norm_ecg
        wr = csv.writer(open('%s_ecg.csv' % outputpath, 'w'), delimiter='\t')
        wr.writerows(zip(xList_interp, norm_yList_interp_csv))
        print('-> %s_ecg.csv' % inputpath)
        #########################################################################

        ######################## 7. JSON FILE CREATION ###########################
        # See http://stackoverflow.com/questions/19697846/python-csv-to-json
        # and https://www.decalage.info/en/python/print_list

        dict_data = {'x': str(xList_interp).strip(
            '[]'), 'y': str(norm_yList_interp_json).strip('[]')}

        jsonfile = open('%s_ecg.json' % outputpath, 'w')
        json.dump(dict_data, jsonfile)
        print('-> %s_ecg.json' % outputpath)
        #########################################################################
else:
    print ('Execution : python exp1.y inputfilepath.dcm')
