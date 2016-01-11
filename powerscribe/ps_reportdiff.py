"""Powerscribe ReportDiff

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
import xml.etree.ElementTree as ET
import powerscribe
import sqlite3
import os,sys,getpass,base64,time,logging

PY3=sys.version_info > (3,) 
if PY3: 
    import diff_match_patch3 as diff_match_patch
else:
    import diff_match_patch

def create_sqlite_table(dbfile):
    conn=sqlite3.connect(dbfile)
    c=conn.cursor()
    create_sql="""create table if not exists study(
                    site text,
                    accession text,
                    timestamp text,
                    proceduredescription text,
                    procedurecode text,
                    modality text,
                    resident text,
                    residentID text,
                    attending text,
                    attendingID text,
                    prelim text,
                    prelim_timestamp text,
                    final text,
                    final_timestamp text,
                    diff_score int,
                    diff_score_percent real,
                    primary key(accession) );"""
    c.execute(create_sql)
    c.close()
    conn.close()

def execute_sql(dbfile,query,params=None):
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
      
def get_prelims(ps,dbfile):   
    print("Checking prelims...")
    result=ps.BrowseOrdersDV(period="PastWeek",orderStatus="Completed",reportStatus="PendingSignature")
    root=ET.fromstring(result)
    prelimset=root.findall('.//VExplorer')
    total_prelims=0
    for elem in prelimset:
        total_prelims+=1
        if powerscribe.get_xml(elem,'.//DictatorLastName') is None: continue
        accession=powerscribe.get_xml(elem,'.//Accession')
        
        reportID=powerscribe.get_xml(elem,'.//ReportID')
        
        result=ps.GetReportChain(reportID)
        report_root=ET.fromstring(result)
        
        prelim_timestamp=powerscribe.get_xml(report_root,'.//b:OriginalReport/b:LastDraftDate')
        check_prelim=execute_sql(dbfile,"select prelim_timestamp from study where accession=?",(accession,))
        if len(check_prelim)>0 and prelim_timestamp==check_prelim[0][0]:
            continue
        
        print("{0}/{1}: updating prelim {2}".format(total_prelims,len(prelimset),accession), end=' ')
        
        dictator_lastname=powerscribe.get_xml(report_root,'.//b:OriginalReport/b:Dictator/b:Person/b:LastName')
        dictator_firstname=powerscribe.get_xml(report_root,'.//b:OriginalReport/b:Dictator/b:Person/b:FirstName')
        dictatorID=powerscribe.get_xml(report_root,'.//b:OriginalReport/b:Dictator/b:AccountID')
        dictator="{0} {1}".format(dictator_firstname,dictator_lastname)
        prelim=powerscribe.get_xml(report_root,'.//b:OriginalReport/b:ContentText')
        modality=powerscribe.get_xml(report_root,'.//b:DiagnosticServSect')
        proceduredescription=powerscribe.get_xml(report_root,'.//b:ProcedureDescList')
        procedure_code=powerscribe.get_xml(report_root,'.//b:ProcedureCodeList')
        timestamp=powerscribe.get_xml(report_root,'.//b:CompleteDate')
        
        
        
        execute_sql(dbfile,"""replace into study (site,accession,timestamp,proceduredescription,procedurecode,
                            modality,resident,residentID,prelim,prelim_timestamp)
                        values (?,?,?,?,?,?,?,?,?,?)""",
                (ps.site,accession,timestamp,proceduredescription,procedure_code,modality,dictator,dictatorID,prelim,prelim_timestamp))   
        print()

def get_finals(ps,dbfile):
    prelimset=execute_sql(dbfile,"select accession from study where final is NULL")
    total_finals=0
    total_prelims=0
    for row in prelimset:
        
        accession=row["accession"]
        total_prelims+=1
        print("{0}/{1}: checking final {2}".format(total_prelims,len(prelimset),accession), end=' ')
        
        result=ps.SearchAccession(accession)
        root=ET.fromstring(result)
        reportID=powerscribe.get_xml(root,'.//ReportID')
        
        if reportID is None:
            print("Missing reportID!")
            execute_sql(dbfile,"""delete from study where accession=?""",(accession,))
            continue
            
        result=ps.GetReportChain(reportID)
        root=ET.fromstring(result)
        
        reportStatus=powerscribe.get_xml(root,'.//b:OriginalReport/b:ReportStatus')

        if reportStatus=="Final":
            print("... adding final report")
            final=powerscribe.get_xml(root,'.//b:OriginalReport/b:ContentText')
            signer_lastname=powerscribe.get_xml(root,'.//b:Signer/b:Person/b:LastName')
            signer_firstname=powerscribe.get_xml(root,'.//b:OriginalReport/b:Signer/b:Person/b:FirstName')
            signerID=powerscribe.get_xml(root,'.//b:OriginalReport/b:Signer/b:AccountID')
            signer="{0} {1}".format(signer_firstname,signer_lastname)
            final_timestamp=powerscribe.get_xml(root,'.//b:OriginalReport/b:LastSignDate')
            execute_sql(dbfile,"""update study set attending=?, attendingID=?, final=?, final_timestamp=? where accession=?""",
                    (signer, signerID, final, final_timestamp, accession))
            total_finals+=1
        print()
    print("Added {0}/{1} final reports".format(total_finals,total_prelims))

def get_diffs(dbfile):
    dmp=diff_match_patch.diff_match_patch()
    dmp.Diff_Timeout=0
    finalset=execute_sql(dbfile,"select * from study where final is not null and diff_score is null")
    for row in finalset:
        accession=row["accession"]
        print("Diff for "+accession)
        prelim=row["prelim"]
        final=row["final"]
        if prelim is not None and final is not None:
            prelim_strip=' '.join(prelim.replace("-"," ").split())
            final_strip=' '.join(final.replace("-"," ").split())
            if len(final_strip)>0:
                d=dmp.diff_main(prelim_strip,final_strip)
                dmp.diff_cleanupSemantic(d)
                diffscore=dmp.diff_levenshtein(d)
                diffpercent=diffscore*100.0/len(final_strip)
                execute_sql(dbfile,"""update study set diff_score=?, diff_score_percent=? where accession=?""",
                        (diffscore,diffpercent,accession))

if __name__=='__main__':    
    site="https://keckpsweb.med.usc.edu"
    dbfile='reportdiff_ps.db'
    create_sqlite_table(dbfile)
    
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
    
    while True:
        try:
            ps=powerscribe.ps_session(site,username,pwd)
            get_prelims(ps,dbfile)
            get_finals(ps,dbfile)         
            get_diffs(dbfile)
        except:
            logging.exception("Error!")
    
            
        for i in range(300,0,-1):
            print("Sleeping for %d seconds....\r" % i, end=' ')
            time.sleep(1)
        print()
