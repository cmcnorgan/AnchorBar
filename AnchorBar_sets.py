#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 12 16:10:39 2022

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
import numpy as np

from random import seed
from random import randint
from random import shuffle

  
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_annot_name(conn, annot_id):
    sql="SELECT shortname FROM annot WHERE annot_id=?;"
    c=conn.execute(sql,[annot_id])
    rst=c.fetchone()
    aname=rst["shortname"]
    return aname

def write_annot(args, conn, rst):
    N_VERTICES=163842
    #default label assignment for all vertices is -1 (UNKNOWN/UNLABELED)
    labels=np.ones(shape=(N_VERTICES,), dtype=int)*-1
    labels.flags.writeable=True
    
    ctab={}
    label_idx=0
    hemi=0
    ctab["Unlabeled"]=(label_idx, 25, 5, 25, 0)
    for r in rst:
        
        #v will be the index into the labels vector for the label id
        v=r["a_v"]
        hemi=r["a_hemi"]
        aname=r["a_name"]
        aabbrev=r["a_abbrev"]
        ar=int(r["a_r"] or 0)
        ag=int(r["a_g"] or 0)
        ab=int(r["a_b"] or 0)
        bname=r["b_name"]
        babbrev=r["b_abbrev"]
        br=int(r["b_r"] or 0)
        bg=int(r["b_g"] or 0)
        bb=int(r["b_b"] or 0)
        
        #use abbreviations if present
        if aabbrev == None:
            A=aname
        else:
            A=aabbrev
        if babbrev == None:
            B=bname
        else:
            B=babbrev
        if A == None:
            A="NULL"
        if B == None:
            B="NULL"
        mergename=(A + "_" + B)
        
        #create new key-value pair if required
        rgb=ctab.get(mergename)
        thislabel=0
        if rgb==None:
            label_idx=label_idx+1
            red=(ar+br)/2
            grn=(ag+bg)/2
            blu=(ab+bb)/2
            
            ctab[mergename]=(label_idx,red,grn,blu,0)
            thislabel=label_idx
        else:
            #key-value pair already exists, store the label_idx
            thislabel=rgb[0]
        labels[v]=thislabel
    
        
    #Next, use the intersected set to make a new annotation.
    #freesurfer.io.write_annot requires:
    #filepath (STR), labels (NDARRAY: nvertices), ctab (NDARRAY: n_labels,5), names (list of STR)
    joiner="_"
    leftname="LEFT"
    rightname="RIGHT"
    if args.intersect != None:
        leftname=get_annot_name(conn, args.intersect[0])
        rightname=get_annot_name(conn, args.intersect[1])
        joiner=".AND."
    if args.union != None:
        leftname=get_annot_name(conn, args.union[0])
        rightname=get_annot_name(conn, args.union[1])
        joiner=".OR."
    h='lh'
    if hemi>0:
        h='rh'
    filepath=(h + "." + leftname + joiner + rightname + ".annot")
    labelnames=[]
    #populate a ctab array from the ctab dict
    n_labels=len(ctab)
        
    ctabarray=np.ndarray(shape=(n_labels,5), dtype=int)
    ctabarray.flags.writeable=True
    for key, value in ctab.items():
        labelnames.append(key)
        irgbt=value
        idx=irgbt[0]-1
        ctabarray[idx]=irgbt
    #drop the first column of the ctab array because I think it's redundant with fill_ctab=True 
    #and was being used in the RGB value, making all the colors blue/green
    fs.io.write_annot(filepath, labels, np.delete(ctabarray,0,1), labelnames, fill_ctab=True)
    print("Saved annotation set operation to %s" % (filepath))

def main():
    
    
    #parse arguments
    parser = argparse.ArgumentParser(description='Manipulate label database')

    parser.add_argument('--db', nargs=1,
                        help='Path to db file')
    parser.add_argument('--intersect', nargs=2, 
                        metavar=('annot_id_1', 'annot_id_2'), help='Intersect labels in two annotations')
    parser.add_argument('--union', nargs=2, 
                        metavar=('annot_id_1', 'annot_id_2'), help='Merges labels in two annotations')
    
    args=parser.parse_args()
    
    if args.db == None:
        sys.exit("Error: db file not provided")
    
    conn=sqlite3.connect(args.db[0])
    c=conn.cursor()
    conn.row_factory=dict_factory
    
    if args.intersect != None:
        sql=("SELECT a_v, a_name, a_abbrev, a_r, a_g, a_b, b_name, b_abbrev, b_r, b_g, b_b, a_hemi FROM "
             "(SELECT vlabels.v AS a_v, "
             "alabels.label_key AS a_label_key, "
             "alabels.hemi AS a_hemi, "
             "alabels.name AS a_name, "
             "alabels.abbrev AS a_abbrev, "
             "alabels.r AS a_r, "
             "alabels.g AS a_g, "
             "alabels.b AS a_b "
             "FROM vlabels INNER JOIN alabels ON "
             "alabels.label_key=vlabels.label_key AND "
             "alabels.annot_id=vlabels.annot_id "
             "WHERE alabels.annot_id=? AND alabels.label_key > 0) "
             "INNER JOIN "
             "(SELECT vlabels.v AS b_v, "
             "alabels.label_key AS b_label_key, "
             "alabels.hemi AS b_hemi, "
             "alabels.name AS b_name, "
             "alabels.abbrev AS b_abbrev, "
             "alabels.r AS b_r, "
             "alabels.g AS b_g, "
             "alabels.b AS b_b "
             "FROM vlabels INNER JOIN alabels ON "
             "alabels.label_key=vlabels.label_key AND "
             "alabels.annot_id=vlabels.annot_id "
             "WHERE alabels.annot_id=? AND alabels.label_key > 0) "
             "ON a_v=b_v AND a_hemi=b_hemi;")
        c=conn.execute(sql,[int(args.intersect[0]), int(args.intersect[1])])
        #This query works as expected
        rst=c.fetchall()
        nset=len(rst)
        
        print("\n*** %d Overlapping Vertices ***" % nset)
        write_annot(args, conn, rst)
    
    if args.union != None:
        sql=("CREATE TEMPORARY TABLE TEMP_LEFTSIDE AS "
	         "SELECT a_v, a_name, a_abbrev, a_r, a_g, a_b, b_name, b_abbrev, b_r, b_g, b_b, a_hemi FROM "
             "(SELECT vlabels.v AS a_v, "
             "alabels.label_key AS a_label_key, "
             "alabels.hemi AS a_hemi, "
             "alabels.name AS a_name, "
             "alabels.abbrev AS a_abbrev, "
             "alabels.r AS a_r, "
             "alabels.g AS a_g, "
             "alabels.b AS a_b "
             "FROM vlabels INNER JOIN alabels ON "
             "alabels.label_key=vlabels.label_key AND "
             "alabels.annot_id=vlabels.annot_id "
             "WHERE alabels.annot_id=? AND alabels.label_key > 0) "
             "LEFT JOIN "
             "(SELECT vlabels.v AS b_v, "
             "alabels.label_key AS b_label_key, "
             "alabels.hemi AS b_hemi, "
             "alabels.name AS b_name, "
             "alabels.abbrev AS b_abbrev, "
             "alabels.r AS b_r, "
             "alabels.g AS b_g, "
             "alabels.b AS b_b "
             "FROM vlabels INNER JOIN alabels ON "
             "alabels.label_key=vlabels.label_key AND "
             "alabels.annot_id=vlabels.annot_id "
             "WHERE alabels.annot_id=? AND alabels.label_key > 0) "
             "ON a_v=b_v AND a_hemi=b_hemi;")
        c=conn.execute(sql,[int(args.union[0]), int(args.union[1])])
        sql=("CREATE TEMPORARY TABLE TEMP_RIGHTSIDE AS "
	         "SELECT a_v, a_name, a_abbrev, a_r, a_g, a_b, b_name, b_abbrev, b_r, b_g, b_b, a_hemi FROM "
             "(SELECT vlabels.v AS a_v, "
             "alabels.label_key AS a_label_key, "
             "alabels.hemi AS a_hemi, "
             "alabels.name AS a_name, "
             "alabels.abbrev AS a_abbrev, "
             "alabels.r AS a_r, "
             "alabels.g AS a_g, "
             "alabels.b AS a_b "
             "FROM vlabels INNER JOIN alabels ON "
             "alabels.label_key=vlabels.label_key AND "
             "alabels.annot_id=vlabels.annot_id "
             "WHERE alabels.annot_id=? AND alabels.label_key > 0) "
             "LEFT JOIN "
             "(SELECT vlabels.v AS b_v, "
             "alabels.label_key AS b_label_key, "
             "alabels.hemi AS b_hemi, "
             "alabels.name AS b_name, "
             "alabels.abbrev AS b_abbrev, "
             "alabels.r AS b_r, "
             "alabels.g AS b_g, "
             "alabels.b AS b_b "
             "FROM vlabels INNER JOIN alabels ON "
             "alabels.label_key=vlabels.label_key AND "
             "alabels.annot_id=vlabels.annot_id "
             "WHERE alabels.annot_id=? AND alabels.label_key > 0) "
             "ON a_v=b_v AND a_hemi=b_hemi;")
        c=conn.execute(sql,[int(args.union[1]), int(args.union[0])])
        c=conn.execute("SELECT DISTINCT * FROM (SELECT * FROM TEMP_LEFTSIDE UNION ALL SELECT * FROM TEMP_RIGHTSIDE) ORDER BY a_v;")
        rst=c.fetchall()
        nset=len(rst)
        conn.execute("DROP TABLE IF EXISTS TEMP_LEFTSIDE;")
        conn.execute("DROP TABLE IF EXISTS TEMP_RIGHTSIDE;")
        print("\n*** %d Overlapping Vertices ***" % nset)
        write_annot(args, conn, rst)
        
    
if __name__ == '__main__':
    main()
    print("")