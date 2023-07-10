#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr 10 15:48:14 2022

@author: CCNLab @buffalo.edu
"""

import os
import shutil
import argparse
import sqlite3
import glob
import sys
import hashlib
import nibabel.freesurfer as fs
import re

from random import seed
from random import randint
from random import shuffle

def hash_file(filename):
    """"This function returns the SHA-1 hash
    of the file passed into it"""
    # make a hash object
    h = hashlib.sha1()
    # open file for reading in binary mode
    with open(filename,'rb') as file:
        # loop till the end of the file
        chunk = 0
        while chunk != b'':
            # read only 1024 bytes at a time
            chunk = file.read(1024)
            h.update(chunk)
    return h




def main():
    #parse arguments
    parser = argparse.ArgumentParser(description='Initialize label database')
    parser.add_argument('--annot', nargs='+',
                        help='List of input .annot files')
    parser.add_argument('--db', nargs=1,
                        help='Path to db file')
    args=parser.parse_args()
    
    #ensure that annotations and hemis line up
    #print(args)
    annotlist=args.annot
    if args.db == None:
        sys.exit("Error: db file not provided")
    if args.annot == None:
        sys.exit("Error: annotation file(s) not provided")
        
    # Arguments should be sensible by this point
    conn=sqlite3.connect(args.db[0])
    c=conn.cursor()
    conn.execute("PRAGMA foreign_keys = 1")
    c.execute('''CREATE TABLE IF NOT EXISTS annot 
              (annot_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
              annot_key string NOT NULL,
              shortname text,
              hemi tinyint NOT NULL, 
              path text NOT NULL,
              fname text NOT NULL,
              UNIQUE(annot_key))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS vlabels 
              (annot_id integer,
              v int, 
              label_key int, 
              FOREIGN KEY(annot_id) REFERENCES annot(annot_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS alabels 
              (label_key int,
              hemi tinyint(2),
              annot_id integer,
              name text,
              abbrev text,
              r tinyint(3), 
              g tinyint(3), 
              b tinyint(3),
              t tinyint(3),
              FOREIGN KEY (annot_id) REFERENCES annot(annot_id))''')

    # Tables guaranteed in database by this point
    # For each .annot, open, hash check for novelty, add if novel
    for a in annotlist:
        #get hash
        filehash=hash_file(a)
        hashbits=filehash.hexdigest()
        filepath=os.path.abspath(a)
        pathname=os.path.dirname(filepath)
        filename=os.path.basename(filepath)
        shortname=re.sub('lh.', '', filename)
        shortname=re.sub('rh.', '', shortname)
        shortname=re.sub('.annot', '', shortname)
        
        hemi=0
        if filename.find('lh.',0,3) > -1:
            hemi=-1
        elif filename.find('rh.',0,3) > -1:
            hemi=1
        if hemi==0:
            print("Skipping %s: Could not infer hemisphere from filename. \nPlease ensure that .annot files are prefixed with 'lh.' or 'rh.'. \n" % a)
            continue
        #look for hash in annot table
        sqlstr="SELECT annot_id FROM annot WHERE annot_key='" + hashbits + "'"
        c.execute(sqlstr) 
        #print(querystr)
        rst = c.fetchone()
        if rst is not None:
            #this annot already exists
            print(rst)
        else:
            #this is a new annot; add it
            #read the annot data
            [vtx, ctab, labelnames]=fs.io.read_annot(a)
            #print(annot)
            #add to annot table
            sql = '''INSERT INTO annot
            (annot_key, shortname, hemi, path, fname)
            VALUES(?, ?, ?, ?, ?);'''
            c.execute(sql,[hashbits, shortname, hemi, pathname, filename])
            conn.commit()
            #lastrowid will have the autoincrement number for the new annot
            annot_id=c.lastrowid
            #add labels to alabels table
            print("Adding labels for %s" %  (a))
            idx=-1
            for l in labelnames:
                idx=idx+1
                rgbt=ctab[idx]
                red=int(rgbt[0])
                grn=int(rgbt[1])
                blu=int(rgbt[2])
                trn=int(rgbt[3])
                tmp=str(l)
                lname=tmp[2:-1]
                conn.execute("INSERT INTO alabels(label_key, name, hemi, annot_id, r, g, b, t) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (idx, lname, hemi, annot_id, red, grn, blu, trn))
                conn.commit()
            #Add vertices
            #Vertex indices --> tks0 : nvertices-1
            idx=-1
            for v in vtx:
                idx=idx+1
                v=int(v)
                conn.execute("INSERT INTO vlabels(label_key, v, annot_id) VALUES (?, ?, ?)", (v, idx, annot_id))
            conn.commit()
            
            
            
            
        
###############################################################################
###############################################################################
###############################################################################
        
if __name__ == '__main__':
    main()
    print("Initialization successful!")
    
