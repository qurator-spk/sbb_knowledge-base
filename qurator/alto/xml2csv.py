#! /usr/bin/env python3

__version__= '1.0'

import argparse
import sys
import os
import numpy as np
import warnings
import xml.etree.ElementTree as et
import pandas as pd
from tqdm import tqdm
import csv

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    
__doc__=\
"""
tool to extract table form data from alto xml data
"""

class xmltocsv:
    def __init__(self,dir, out_dir):
        self.dir=dir
        self.output_dir=out_dir
    
    def get_content_of_dir(self):
        """
        Listing all sub-directories which are named with PPn
        """

        self.ppn_list=os.listdir(self.dir)
         
    def get_features(self):
        """
        Extracting features needed for text mining. 
        """
        self.feature_ppn=[]
        self.feature_text=[]
        self.feature_wc=[]
        self.feature_file_name=[]

        headers=['file name', 'text' ,'wc', 'ppn']
        
        with open(self.output_dir+"/xml2csv_alto.csv",'w') as f:
            writer=csv.writer(f)
            writer.writerow(headers)
            
            for ppn_ind in tqdm(self.ppn_list):
                
    
                self.c_d=os.listdir(self.dir+'/'+ppn_ind)
                for f_n in self.c_d:
                    try:
                        tree=et.parse(self.dir+'/'+ppn_ind+'/'+f_n)
                        root=tree.getroot()
        
                        text_s=[]
                        wc_s=[]
           
                        for str_ind in root.iter('{http://www.loc.gov/standards/alto/ns-v2#}String'):
                            if 'WC' in str_ind.attrib:
                                wc_s.append(str_ind.attrib['WC'])
                            else:
                                wc_s.append(str(np.NAN))
                                
                            if 'CONTENT' in str_ind.attrib:
                                text_s.append(str_ind.attrib['CONTENT'])  
                            else:
                                text_s.append(str(np.NAN))
                                
                        writer.writerow([f_n, " ".join(text_s), " ".join(wc_s), ppn_ind] )
                    except:
                        pass

    def run(self):
        self.get_content_of_dir()
        self.get_features()
def main():
    parser=argparse.ArgumentParser()
    
    parser.add_argument('-dir_in','--dir_in', dest='inp1', default=None, help='directory of alto files which have to be transformed')
    parser.add_argument('-dir_out','--dir_out', dest='inp2', default=None, help='directory for output and the name of output file will be xml2csv_alto.csv')

    options=parser.parse_args()
    possibles=globals()
    possibles.update(locals())
    x=xmltocsv(options.inp1,options.inp2)
    x.run()  
if __name__=="__main__":
    main()

    
    
    
