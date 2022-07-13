#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse,sys
import pyodbc
from pickle import TRUE
import warnings
warnings.simplefilter("ignore", UserWarning)
from lib2to3.pgen2 import pgen
from datetime import datetime
import os
from subprocess import *


__author__ = "Alejandro Sánchez Carrion"
__copyright__ = "Copyright 2021, PandoraFMS"
__maintainer__ = "Projects department"
__status__ = "Production"
__version__ = "18042022"

description= f"""
Pandora_postgresql tool ver {__version__}

Execute query againts Azure SQL database from configuration file 

Example config file:
module_name:query:type:description
number_connections:SELECT TOP 3 name, collation_name FROM sys.databases:generic_data:Number of Connections or running backend

""" 

parser = argparse.ArgumentParser(description= description, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-d', '--database', help='Name of the database', required=True)
parser.add_argument('-u', '--user', help='AzureSQL username', required=True)
parser.add_argument('-p', '--password', help='AzureSQL password',required=True )
parser.add_argument('-s', '--servidor', help='Server name', required=True)
parser.add_argument('--tentacle_port', help='tentacle port', default=41121)
parser.add_argument('--tentacle_address', help='tentacle adress', default=None)
parser.add_argument('--agent_name', help='Name of the agent', default= "AzureSQL")
parser.add_argument('--prefix_module', help='Prefix module')
parser.add_argument('--conf', help='path for the file with the queries',required=True)
parser.add_argument('-g', '--group', help='PandoraFMS destination group (default azure)', default='Azure')
parser.add_argument('--data_dir', help='PandoraFMS data dir (default: /var/spool/pandora/data_in/)', default='/var/spool/pandora/data_in/')
parser.add_argument('--as_agent_plugin', help='mode plugin', default=0,type=int)


args = parser.parse_args()

### Pandora Tools ###-------------------------------------------------------------------------------------------------------
modules = []

config = {
    "data_in": args.data_dir,
    "group" : args.group
}

#########################################################################################
# print_agent
#########################################################################################
def print_agent(agent, modules, data_dir="/var/spool/pandora/data_in/", log_modules= None, print_flag = None):
    """Prints agent XML. Requires agent conf (dict) and modules (list) as arguments.
    - Use print_flag to show modules' XML in STDOUT.
    - Returns a tuple (xml, data_file).
    """
    data_file=None

    header = "<?xml version='1.0' encoding='UTF-8'?>\n"
    header += "<agent_data"
    for dato in agent:
        header += " " + str(dato) + "='" + str(agent[dato]) + "'"
    header += ">\n"
    xml = header
    if modules :
        for module in modules:
            modules_xml = print_module(module)
            xml += str(modules_xml)
    if log_modules :
        for log_module in log_modules:
            modules_xml = print_log_module(log_module)
            xml += str(modules_xml)
    xml += "</agent_data>"
    if not print_flag:
        data_file = write_xml(xml, agent["agent_name"], data_dir)
    else:
        print(xml)
    
    return (xml,data_file)

#########################################################################################
# print_module
#########################################################################################
def print_module(module, print_flag=None):
    """Returns module in XML format. Accepts only {dict}.\n
    - Only works with one module at a time: otherwise iteration is needed.
    - Module "value" field accepts str type or [list] for datalists.
    - Use print_flag to show modules' XML in STDOUT.
    """
    data = dict(module)
    module_xml = ("<module>\n"
                  "\t<name><![CDATA[" + str(data["name"]) + "]]></name>\n"
                  "\t<type>" + str(data["type"]) + "</type>\n"
                  )
    
    if type(data["type"]) is not str and "string" not in data["type"]: #### Strip spaces if module not generic_data_string
        data["value"] = data["value"].strip()
    if isinstance(data["value"], list): # Checks if value is a list
        module_xml += "\t<datalist>\n"
        for value in data["value"]:
            if type(value) is dict and "value" in value:
                module_xml += "\t<data>\n"
                module_xml += "\t\t<value><![CDATA[" + str(value["value"]) + "]]></value>\n"
                if "timestamp" in value:
                    module_xml += "\t\t<timestamp><![CDATA[" + str(value["timestamp"]) + "]]></timestamp>\n"
            module_xml += "\t</data>\n"
        module_xml += "\t</datalist>\n"
    else:
        module_xml += "\t<data><![CDATA[" + str(data["value"]) + "]]></data>\n"
    if "desc" in data:
        module_xml += "\t<description><![CDATA[" + str(data["desc"]) + "]]></description>\n"
    if "unit" in data:
        module_xml += "\t<unit><![CDATA[" + str(data["unit"]) + "]]></unit>\n"
    if "interval" in data:
        module_xml += "\t<module_interval><![CDATA[" + str(data["interval"]) + "]]></module_interval>\n"
    if "tags" in data:
        module_xml += "\t<tags>" + str(data["tags"]) + "</tags>\n"
    if "module_group" in data:
        module_xml += "\t<module_group>" + str(data["module_group"]) + "</module_group>\n"
    if "module_parent" in data:
        module_xml += "\t<module_parent>" + str(data["module_parent"]) + "</module_parent>\n"
    if "min_warning" in data:
        module_xml += "\t<min_warning><![CDATA[" + str(data["min_warning"]) + "]]></min_warning>\n"
    if "min_warning_forced" in data:
        module_xml += "\t<min_warning_forced><![CDATA[" + str(data["min_warning_forced"]) + "]]></min_warning_forced>\n"
    if "max_warning" in data:
        module_xml += "\t<max_warning><![CDATA[" + str(data["max_warning"]) + "]]></max_warning>\n"
    if "max_warning_forced" in data:
        module_xml += "\t<max_warning_forced><![CDATA[" + str(data["max_warning_forced"]) + "]]></max_warning_forced>\n"
    if "min_critical" in data:
        module_xml += "\t<min_critical><![CDATA[" + str(data["min_critical"]) + "]]></min_critical>\n"
    if "min_critical_forced" in data:
        module_xml += "\t<min_critical_forced><![CDATA[" + str(data["min_critical_forced"]) + "]]></min_critical_forced>\n"
    if "max_critical" in data:
        module_xml += "\t<max_critical><![CDATA[" + str(data["max_critical"]) + "]]></max_critical>\n"
    if "max_critical_forced" in data:
        module_xml += "\t<max_critical_forced><![CDATA[" + str(data["max_critical_forced"]) + "]]></max_critical_forced>\n"
    if "str_warning" in data:
        module_xml += "\t<str_warning><![CDATA[" + str(data["str_warning"]) + "]]></str_warning>\n"
    if "str_warning_forced" in data:
        module_xml += "\t<str_warning_forced><![CDATA[" + str(data["str_warning_forced"]) + "]]></str_warning_forced>\n"
    if "str_critical" in data:
        module_xml += "\t<str_critical><![CDATA[" + str(data["str_critical"]) + "]]></str_critical>\n"
    if "str_critical_forced" in data:
        module_xml += "\t<str_critical_forced><![CDATA[" + str(data["str_critical_forced"]) + "]]></str_critical_forced>\n"
    if "critical_inverse" in data:
        module_xml += "\t<critical_inverse><![CDATA[" + str(data["critical_inverse"]) + "]]></critical_inverse>\n"
    if "warning_inverse" in data:
        module_xml += "\t<warning_inverse><![CDATA[" + str(data["warning_inverse"]) + "]]></warning_inverse>\n"
    if "max" in data:
        module_xml += "\t<max><![CDATA[" + str(data["max"]) + "]]></max>\n"
    if "min" in data:
        module_xml += "\t<min><![CDATA[" + str(data["min"]) + "]]></min>\n"
    if "post_process" in data:
        module_xml += "\t<post_process><![CDATA[" + str(data["post_process"]) + "]]></post_process>\n"
    if "disabled" in data:
        module_xml += "\t<disabled><![CDATA[" + str(data["disabled"]) + "]]></disabled>\n"
    if "min_ff_event" in data:
        module_xml += "\t<min_ff_event><![CDATA[" + str(data["min_ff_event"]) + "]]></min_ff_event>\n"
    if "status" in data:
        module_xml += "\t<status><![CDATA[" + str(data["status"]) + "]]></status>\n"
    if "timestamp" in data:
        module_xml += "\t<timestamp><![CDATA[" + str(data["timestamp"]) + "]]></timestamp>\n"
    if "custom_id" in data:
        module_xml += "\t<custom_id><![CDATA[" + str(data["custom_id"]) + "]]></custom_id>\n"
    if "critical_instructions" in data:
        module_xml += "\t<critical_instructions><![CDATA[" + str(data["critical_instructions"]) + "]]></critical_instructions>\n"
    if "warning_instructions" in data:
        module_xml += "\t<warning_instructions><![CDATA[" + str(data["warning_instructions"]) + "]]></warning_instructions>\n"
    if "unknown_instructions" in data:
        module_xml += "\t<unknown_instructions><![CDATA[" + str(data["unknown_instructions"]) + "]]></unknown_instructions>\n"
    if "quiet" in data:
        module_xml += "\t<quiet><![CDATA[" + str(data["quiet"]) + "]]></quiet>\n"
    if "module_ff_interval" in data:
        module_xml += "\t<module_ff_interval><![CDATA[" + str(data["module_ff_interval"]) + "]]></module_ff_interval>\n"
    if "crontab" in data:
        module_xml += "\t<crontab><![CDATA[" + str(data["crontab"]) + "]]></crontab>\n"
    if "min_ff_event_normal" in data:
        module_xml += "\t<min_ff_event_normal><![CDATA[" + str(data["min_ff_event_normal"]) + "]]></min_ff_event_normal>\n"
    if "min_ff_event_warning" in data:
        module_xml += "\t<min_ff_event_warning><![CDATA[" + str(data["min_ff_event_warning"]) + "]]></min_ff_event_warning>\n"
    if "min_ff_event_critical" in data:
        module_xml += "\t<min_ff_event_critical><![CDATA[" + str(data["min_ff_event_critical"]) + "]]></min_ff_event_critical>\n"
    if "ff_type" in data:
        module_xml += "\t<ff_type><![CDATA[" + str(data["ff_type"]) + "]]></ff_type>\n"
    if "ff_timeout" in data:
        module_xml += "\t<ff_timeout><![CDATA[" + str(data["ff_timeout"]) + "]]></ff_timeout>\n"
    if "each_ff" in data:
        module_xml += "\t<each_ff><![CDATA[" + str(data["each_ff"]) + "]]></each_ff>\n"
    if "module_parent_unlink" in data:
        module_xml += "\t<module_parent_unlink><![CDATA[" + str(data["parent_unlink"]) + "]]></module_parent_unlink>\n"
    if "global_alerts" in data:
        for alert in data["alert"]:
            module_xml += "\t<alert_template><![CDATA[" + alert + "]]></alert_template>\n"
    module_xml += "</module>\n"

    if print_flag:
        print (module_xml)

    return (module_xml)

#########################################################################################
# write_xml
#########################################################################################

def write_xml(xml, agent_name, data_dir="/var/spool/pandora/data_in/"):
    """Creates a agent .data file in the specified data_dir folder\n
    Args:
    - xml (str): XML string to be written in the file.
    - agent_name (str): agent name for the xml and file name.
    - data_dir (str): folder in which the file will be created."""
    Utime = datetime.now().strftime('%s')
    data_file = "%s/%s.%s.data" %(str(data_dir),agent_name,str(Utime))
    try:
        with open(data_file, 'x') as data:
            data.write(xml)
    except OSError as o:
        sys.exit(f"ERROR - Could not write file: {o}, please check directory permissions")
    except Exception as e:
        sys.exit(f"{type(e).__name__}: {e}")
    return (data_file)

# # default agent
def clean_agent() :
    global agent
    agent = {
        "agent_name"  : "",
        "agent_alias" : "",
        "parent_agent_name" : "",
        "description" : "",
        "version"     : "",
        "os_name"     : "",
        "os_version"  : "",
        "timestamp"   : datetime.today().strftime('%Y/%m/%d %H:%M:%S'),
        #"utimestamp"  : int(datetime.timestamp(datetime.today())),
        "address"     : "",
        "group"       : config["group"],
        "interval"    : "",
        "agent_mode"  : "1",
        }
    return agent

# default module
def clean_module() :
    global modulo
    modulo = {
        "name"   : "",
        "type"   : "generic_data_string",
        "desc"   : "",
        "value"  : "",
    }
    return modulo

#########################################################################################
# tentacle_xml
#########################################################################################
def tentacle_xml(file, tentacle_ops,tentacle_path='', debug=0):
    """Sends file using tentacle protocol\n
    - Only works with one file at time.
    - file variable needs full file path.
    - tentacle_opts should be a dict with tentacle options (address [password] [port]).
    - tentacle_path allows to define a custom path for tentacle client in case is not in sys path).
    - if debug is enabled, the data file will not be removed after being sent.

    Returns 0 for OK and 1 for errors.
    """

    if file is None :
        sys.stderr.write("Tentacle error: file path is required.")
    else :
        data_file = file
    
    if tentacle_ops['address'] is None :
        sys.stderr.write("Tentacle error: No address defined")
        return 1
    
    try :
        with open(data_file, 'r') as data:
            data.read()
        data.close()
    except Exception as e :
        sys.stderr.write(f"Tentacle error: {type(e).__name__} {e}")
        return 1

    tentacle_cmd = f"{tentacle_path}tentacle_client -v -a {tentacle_ops['address']} "
    if "port" in tentacle_ops:
        tentacle_cmd += f"-p {tentacle_ops['port']} "
    if "password" in tentacle_ops:
        tentacle_cmd += f"-x {tentacle_ops['password']} "
    tentacle_cmd += f"{data_file} "

    tentacle_exe=Popen(tentacle_cmd, stdout=PIPE, shell=True)
    rc=tentacle_exe.wait()

    if rc != 0 :
        sys.stderr.write("Tentacle error")
        return 1
    elif debug == 0 : 
        os.remove(file)
 
    return 0

## funcion agent
def agentplugin(modules,agent,plugin_type="server",data_dir="/var/spool/pandora/data_in/",tentacle=False,tentacle_conf=None) :
    if plugin_type == "server":
        for modulo in modules:
            print_module(modulo,1)
        
    elif tentacle == True and tentacle_conf is not None:
        agent_file=print_agent(agent, modules,data_dir)
        if agent_file[1] is not None:
            tentacle_xml(agent_file[1],tentacle_conf)
            print ("1")        
    else:
        print_agent(agent, modules,data_dir)
        print ("1")    


        


#######################FUNCIONES STATS############################################----------------------------------------------------------------------------
adatabase = args.database
auser=args.user
apassword=args.password
aserver=args.servidor
name_agent=args.agent_name
as_agent_plugin = args.as_agent_plugin
prefix_module=args.prefix_module

clean_agent()
agent.update(
    agent_name = name_agent ,
    agent_alias =name_agent , 
    description ="PostgreSQL agent"  
)  

def translate_macro(macro_dic: dict, data: str) :
    """expects a macro dictionary key:value (macro_name:macro_value) and a string to replace macro.
    It will replace the macro_name for the macro_value in any string.
    """
    for macro_name, macro_value in macro_dic.items():
        data = data.replace(macro_name, macro_value) 

    #print (data)
    return data

def parse_result(c_query,sep=";")-> list:
    """
    + Return list containing each line as element
    """    
        
    result=[]

    for line in c_query:
        str_line=sep.join(str(elem) for elem in line)
        str_dict={"value":str_line}
        result.append(str_dict)

    return result
            
driver= '{ODBC Driver 18 for SQL Server}'            

def connect():
    """
    + connecting to the database 
    + using the connect function
    + creating the cursor object
    + returning the conn and cur objects to be used later 
    """
    try:

        conn = pyodbc.connect('DRIVER='+driver+';SERVER=tcp:'+aserver+';PORT=1433;DATABASE='+adatabase+';UID='+auser+';PWD='+ apassword)

        # creating the cursor object
        cur = conn.cursor()

    except Exception as error:

        print ("Error while creating PostgreSQL table", error)

    # returing the conn and cur 
    # objects to be used later 
    return conn, cur 

       

path_conf=args.conf

## CUSTOM QUERIES

def custom_query():
 
    """
    + Create module for each custom query
    """

    conn, cur = connect() 

    try:
        f = open(path_conf, "r")
    except (Exception) as error:
        print ("Error al conectarse", error)

    
    for linea in f:
        if linea == "\n":
            continue
        if '#' in linea:
            continue

        line = linea.split(":")

        if len(line) < 3:
            print ("It is mandatory to specify name, query and type!")
            exit()

        pandora_macros = {
            '_database_' : "'"+adatabase+"'"
        }
       
        name_module=line[0]
        query = line[1]
        
        #translate_macro(pandora_macros,query)
        data=translate_macro(pandora_macros,query)

        type_module = line[2]
        type_module=type_module.strip()
        
        if len(line)==4:
            descrip=line[3]
        else:
            descrip=""

        try: 
            cur.execute(str(data.strip())) 
            c_query = cur.fetchall() 
        except Exception as e: 
            print(f'error with the query:{data}.{e}',file = sys.stderr )
            continue


        result_query = parse_result(c_query)
        
        
        if prefix_module:

            clean_module()
            modulo.update(
                name = prefix_module + "_" + name_module,
                type = type_module,
                desc = descrip,
                value = result_query
            )
            modules.append(modulo)
   
        else:
            clean_module()
            modulo.update(
                name = name_module,
                type = type_module,
                desc = descrip,
                value = result_query
            )
            modules.append(modulo)
    f.close()    


try:
    custom_query()
except Exception as e: 
    print(f'Error: {e}',file = sys.stderr )  
    print ("0")
    exit()
    

if args.tentacle_address is not None:
    tentacle_conf={"address":args.tentacle_address,"port":args.tentacle_port}
    agentplugin(modules,agent,"agent",config["data_in"],True,tentacle_conf)
elif as_agent_plugin==1:
    agentplugin(modules,agent,"agent",config["data_in"]) 
else:
    agentplugin(modules,agent) 
