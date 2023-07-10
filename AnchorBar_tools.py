#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 12 16:10:39 2022

@author: CCNLab @buffalo.edu
"""

import os
import argparse
import sqlite3
import sys
import hashlib
import nibabel.freesurfer as fs


"""
For future colors reference:
    
https://stackoverflow.com/questions/470690/how-to-automatically-generate-n-distinct-colors
"""

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def main():
    #parse arguments
    parser = argparse.ArgumentParser(description='Manipulate label database')
    parser.add_argument('--list', action='store_true',
                        help='List annotations')
    parser.add_argument('--labels', nargs=1, metavar=('annot_id'),
                        help='List labels for annotation')
    parser.add_argument('--drop', nargs=1, metavar=('annot_id'), 
                        help='Drop annotation from database')
    parser.add_argument('--db', nargs=1,
                        help='Path to db file')
    parser.add_argument('--rename', nargs=2, 
                        metavar=('annot_id', 'new_shortname'), 
                        help='Assign new shortname to annotation')
    parser.add_argument('--relabel', nargs=3, 
                        metavar=('annot_id', 'label_id', 'new_label_name'), 
                        help='Assign new name to label')
    parser.add_argument('--reassign', nargs=3, 
                        metavar=('annot_id', 'old_label_id', 'new_label_id'), 
                        help='Reassign annotation vertices from one label to another')
    
    parser.add_argument('--abbrev', nargs=3, 
                        metavar=('annot_id', 'label_id', 'abbrev_label_name'), 
                        help='Assign new abbreviated label name')
        
    args=parser.parse_args()
    
    if args.db == None:
        sys.exit("Error: db file not provided")
            
    
    conn=sqlite3.connect(args.db[0])
    c=conn.cursor()
    conn.row_factory=dict_factory
    
    #Rename (shortname) of annotation?
    if args.rename != None:
        annot_id=args.rename[0]
        shortname=args.rename[1]
        sql = '''UPDATE annot SET shortname=? WHERE annot_id=?'''
        c.execute(sql,[shortname, annot_id])
        conn.commit()
        
    #Rename label?
    if args.relabel != None:
        annot_id=args.relabel[0]
        label_id=args.relabel[1]
        newname=args.relabel[2]
        sql = '''UPDATE alabels SET name=? WHERE annot_id=? AND label_key=?'''
        c.execute(sql,[newname, annot_id, label_id])
        conn.commit()
        
    if args.reassign != None:
        annot_id=args.reassign[0]
        old_label_id=args.reassign[1]
        new_label_id=args.reassign[2]
        sql = '''UPDATE vlabels SET label_key=? WHERE annot_id=? AND label_key=?'''
        c.execute(sql, [new_label_id, annot_id, old_label_id])
        sql = '''DELETE FROM alabels WHERE annot_id=? AND label_key=?'''
        c.execute(sql, [annot_id, old_label_id])
        conn.commit()
        
    #Assign label abbreviation?
    if args.abbrev != None:
        annot_id=args.abbrev[0]
        label_id=args.abbrev[1]
        newname=args.abbrev[2]
        sql = '''UPDATE alabels SET abbrev=? WHERE annot_id=? AND label_key=?'''
        c.execute(sql,[newname, annot_id, label_id])
        conn.commit()

    #Drop annotation?
    if args.drop != None:
        annot_id=int(args.drop[0])
        sql='''DELETE from alabels WHERE annot_id=?'''
        c=conn.execute(sql,[annot_id])
        sql='''DELETE from annot WHERE annot_id=?'''
        c=conn.execute(sql,[annot_id])
        sql='''DELETE from vlabels WHERE annot_id=?'''
        c=conn.execute(sql,[annot_id])
        conn.commit()
        print("\n*** Annotation Dropped ***\n")
        args.list=True
        
    #List annotations?
    if args.list:
        c=conn.execute("SELECT * FROM annot")
        rst=c.fetchall()
        print("\n*** Annotation List ***\nid\tLR shortname\tpath")
        for r in rst:
            annot_id=r["annot_id"]
            shortname=r["shortname"]
            hemi=r["hemi"]
            h="lh"
            if hemi > 0:
                h="rh"
            path=r["path"]
            print("%d\t%s %s\t%s" % (annot_id, h, shortname, path))
    

    #List labels?
    if args.labels != None:
        #thinking of being fancy and using colorama to print labels in color
        sql='''SELECT label_key, name, abbrev FROM alabels WHERE annot_id=?'''
        c=conn.execute(sql,[int(args.labels[0])])
        rst=c.fetchall()
        print("\n*** Annotation %s labels ***" % args.labels[0])
        for r in rst:
            label_key=r["label_key"]
            name=r["name"]
            abbrev=r["abbrev"]
            print("%d\t%s\t%s" %(label_key, name, abbrev))
            
    
       
    
if __name__ == '__main__':
    main()
    print("")