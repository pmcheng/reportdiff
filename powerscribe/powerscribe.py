"""Powerscribe Utility Methods

Copyright 2015-2019 Phillip Cheng, MD MS

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
try:
    from urllib.request import urlopen,Request
except ImportError:
    from urllib2 import urlopen,Request
import xml.etree.ElementTree as ET
import getpass
import base64

namespaces = {'b': 'http://schemas.datacontract.org/2004/07/Nuance.Radiology.Services.Contracts',
              'c': 'http://schemas.microsoft.com/2003/10/Serialization/Arrays',
              's': 'http://www.w3.org/2003/05/soap-envelope', 
              'a': 'http://www.w3.org/2005/08/addressing',
              'i': 'http://www.w3.org/2001/XMLSchema-instance'}          

def get_xml(elem,subelem):
    if elem.find(subelem,namespaces=namespaces) is not None:
        return elem.find(subelem,namespaces=namespaces).text
    else:
        return None
                         
class ps_session():
    """Collection of methods using a connection to a Powerscribe 360 server
    """
    
    def __init__(self,site,username="",password=""):
        self.site=site    
        self.session=""
        self.SignIn(username,password)        
    
    def SignIn(self,username="",password=""):
        """Sign in to Powerscribe 360"""
        if username=="":
            username=getpass.getpass('Username:')
        if password=="":
            password=getpass.getpass('Password:')
        service="session.svc"
        action="Authentication/SignIn"
        params="""<healthSystemID>1</healthSystemID><accessCode i:nil="true" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"/><loginName>"""+username+"""</loginName><password>"""+password+"""</password><adminMode>false</adminMode><version>7.0.154.0</version><workstation></workstation>"""
        data=self.envelope(service,action,params)
        response=self.request(service,data)
        root=ET.fromstring(response)
        self.session=root.find('.//AccountSession').text
    
      
    def envelope(self, service, action, params):
        """Create a SOAP envelope for a session to a PS360 service for an action"""
        session_string=""
        if self.session!="":
            session_string="""<AccountSession>"""+self.session+"""</AccountSession>"""
        url=self.site+"/RAS/"+service
        header="""<s:Header><a:Action s:mustUnderstand="1">Nuance/Radiology/Services/2010/01/"""+action+"""</a:Action>"""+session_string+"""<a:To s:mustUnderstand="1">"""+url+"""</a:To></s:Header>"""
    
        averb=action[action.rfind("/")+1:]
        body="""<s:Body><"""+averb+""" xmlns="Nuance/Radiology/Services/2010/01">"""+params+"""</"""+averb+"""></s:Body>"""
    
        return """<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://www.w3.org/2005/08/addressing">""" + header + body + """</s:Envelope>"""
            
    def request(self, service, data):
        url=self.site+"/RAS/"+service
        req=Request(url,data.encode('ascii'),headers={'Content-type':'application/soap+xml'})
        return urlopen(req).read()
    
    
    def SearchAccession(self,accession):
        service="explorer.svc"
        action="OrderExplorer/QuickSearchDV"
        params="""<siteID>0</siteID><searchType>Accession</searchType><values xmlns:b="http://schemas.microsoft.com/2003/10/Serialization/Arrays" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"><b:string>"""+accession+"""</b:string></values>"""    
        data=self.envelope(service,action,params)
        response=self.request(service,data)
        return response
    
    def GetReportChain(self,reportID):
        service="report.svc"
        action="ReportManagement/GetReportChain"
        params="""<reportID>"""+reportID+"""</reportID><fetchBlob>false</fetchBlob>"""
        data=self.envelope(service,action,params)
        response=self.request(service,data)
        return response
    
    def GetReport(self,reportID):
        service="report.svc"
        action="ReportManagement/GetReport"
        params="""<reportID>"""+reportID+"""</reportID><fetchBlob>false</fetchBlob>"""
        data=self.envelope(service,action,params)
        response=self.request(service,data)
        return response
    
    def GetAccount(self,accountID):
        service="account.svc"
        action="AccountManagement/GetAccount"
        params="""<accountID>"""+accountID+"""</accountID>"""
        data=self.envelope(service,action,params)
        response=self.request(service,data)
        return response
        
    def GetAccountNames(self):
        service="account.svc"
        action="AccountManagement/GetAccountNames"
        params="""<siteIDs xmlns:b="http://schemas.microsoft.com/2003/10/Serialization/Arrays" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"><b:int>1</b:int></siteIDs><auth>Radiologist</auth>"""
        data=self.envelope(service,action,params)
        response=self.request(service,data)
        accounts=[]
        root=ET.fromstring(response)
        for account in root.findall('.//b:IDNamePair',namespaces=namespaces):
            accounts.append((get_xml(account,'.//b:ID'),get_xml(account,'.//b:Name')))
        return accounts
        
    def GetAccountReportCount(self,query):
        service="explorer.svc"
        action="OrderExplorer/GetAccountReportCount"
        params="""<query>"""+query+"""</query>"""
        data=self.envelope(service,action,params)
        response=self.request(service,data)
        return response
    
    def BrowseOrdersDV(self,period="PastWeek",orderStatus="All",reportStatus="All",accountID=0, modality=0, anatomy=0, fromdate="0001-01-01T00:00:00",todate="0001-01-01T00:00:00"):
    
        # period = PastHour PastFourHours Today Yesterday PastTwoDays PastThreeDays PastWeek PastTwoWeeks PastMonth Tomorrow AllFuture NoLimit Custom
        # orderStatus = All Scheduled Completed Temporary Cancelled DictatedExt Entered
        
        # reportStatus = All WetRead Draft PendingCorrection Corrected CorrectionRejected PendingSignature SignRejected Final NonFinal Addended Rejected Reported Unreported
        
        # use NonFinal for Draft, PendingSignature
        # use PendingSignature for resident/fellow reports

        # anatomy = 311 Abdomen & Pelvis, 316 chest
        # modality = 22 CT, 220 MR, 24 US, 27 Fluoro, 21 Radiography

        service="explorer.svc"
        action="OrderExplorer/BrowseOrdersDV"
        params="""<time xmlns:b="http://schemas.datacontract.org/2004/07/Nuance.Radiology.Services.Contracts" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"><b:From>{0}</b:From><b:Period>{1}</b:Period><b:To>{2}</b:To></time><orderStatus>{3}</orderStatus><reportStatus>{4}</reportStatus><accountID>{5}</accountID><modality>{6}</modality><anatomy>{7}</anatomy>""".format(fromdate,period,todate,orderStatus,reportStatus,accountID,modality,anatomy)
        data=self.envelope(service,action,params)
        response=self.request(service,data)
        return response

if __name__=='__main__':
    site="http://calv-psapp"

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

    ps=ps_session(site,username,pwd)
    
    result=ps.GetAccountReportCount("SigningQueue")
    print("SigningQueue: ",result)
    
    result=ps.SearchAccession("330-CT-14-006404")
    print("SearchAccession: ",result)

    root=ET.fromstring(result)
    reportID=root.find('.//ReportID').text
    
    result=ps.GetReportChain(reportID)
  
    root=ET.fromstring(result)
    content=root.find('.//b:ContentText',namespaces=namespaces).text
    print("ReportContent: ",content)
       
    result=ps.GetAccountNames()
    print(result)
    
    (userid,username)=result[0]
    print("GetAccount for "+username+": "+ps.GetAccount(userid))
    
    result=ps.BrowseOrdersDV(period="PastThreeDays",reportStatus="PendingSignature")
    print(result)
