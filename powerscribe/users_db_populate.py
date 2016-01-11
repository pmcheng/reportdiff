"""ReportDiff user database initialization and update

Run this script to initialize and update the user database for ReportDiff Flask 
server using data from a Powerscribe 360 server.

Copyright 2015-2016 Phillip Cheng, MD MS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import print_function
import sqlite3
import base64,powerscribe
import xml.etree.ElementTree as ET
import os

def execute_sql(dbfile,query,params=None):
    """Execute SQL against a SQLite file
    
    Args:
        dbfile: SQLite database file
        query: SQL query
        params: sequence of parameters
    
    Returns:
        list of matching rows
    """
    conn=sqlite3.connect(dbfile)
    conn.row_factory=sqlite3.Row
    c=conn.cursor()
    
    try:
        if params is None:
            c.execute(query)
        else:
            c.execute(query,params)
        res=c.fetchall()
    except sqlite3.OperationalError as e:
        print(e)
        res=None
    c.close()
    conn.commit()
    conn.close()
    return res

    
if __name__=='__main__':    
    dbfile='users.db'    
    execute_sql(dbfile,'''CREATE TABLE if not exists users
        (
            id integer primary key autoincrement,
            username text,
            role int,
            password text,
            firstname text,
            lastname text,
            nickname text,
            ps_id text,
            grad_date text
        )''')
    execute_sql(dbfile,'''CREATE TABLE if not exists logins
        (
            id integer primary key autoincrement,
            user_id text,
            timestamp text
        )''')

    execute_sql(dbfile,'''CREATE TABLE if not exists report_views
        (
            id integer primary key autoincrement,
            user_id text,
            accession text,
            timestamp text
        )''')

        
    site="https://keckpsweb.med.usc.edu"
    
    try:
        input = raw_input
    except NameError:
        pass
    
    login=os.getenv("SYNLOGIN")
    if login is not None:
        (username,pwd)=base64.b64decode(login.encode('ascii')).decode('ascii').split("|")
    else:
        username=input("Username [%s]: " % getpass.getuser())
        pwd=getpass.getpass()
    
    ps=powerscribe.ps_session(site,username,pwd)
    
    result=ps.GetAccountNames()
    for (ID,name) in result:
        print(ID,name)
        result=ps.GetAccount(ID)
        root=ET.fromstring(result)
        username=powerscribe.get_xml(root,'.//b:UserName')
        role=powerscribe.get_xml(root,'.//b:Role')
        firstname=powerscribe.get_xml(root,'.//b:FirstName')
        lastname=powerscribe.get_xml(root,'.//b:LastName')
        if role=="Attending":
            roleID=1
        else:
            roleID=0
        password="trojan"
        nickname=""
        if len(execute_sql(dbfile,"select * from users where username=?",(username,)))==0:
            print("===> ",firstname,lastname)
            execute_sql(dbfile,"insert into users (username,role,password,firstname,lastname,nickname,ps_id) values (?,?,?,?,?,?,?)", (username,roleID,password,firstname,lastname,nickname,ID))
    