#!/usr/bin/env python3

import subprocess, sys, os, shutil
import re
import datetime, time, pytz
from mainBOB import getidforBOB

def rebootPI():
    #reboot pi now
    subprocess.call("shutdown -r now", shell=True)

def logACTION(match):
    #do an action based on match or not
    #if match...all is well so exit
    if match:
        with open ("/opt/BOB/logs/theminion.log", "a") as log:
            checkerzone = pytz.timezone('America/Chicago')
            checkertime = datetime.datetime.now(tz=checkerzone)
            log.write(f"{checkertime} pythonchecker reports that mainBOB is running!\n")
        log.close()
        #ftp the file off
        ftpMINION()
        sys.exit()
    #if no match, issue log and reboot
    else:
        #get the current time
        checkerzone = pytz.timezone('America/Chicago')
        checkertime = datetime.datetime.now(tz=checkerzone)
        with open ("/opt/BOB/logs/theminion.log", "a") as log:
            log.write(f"{checkertime} pythonchecker reports that mainBOB was not running. Rebooted!\n")
        log.close()
        #ftp the file off
        ftpMINION()
        rebootPI()

def deploySEARCH():
    #search to see if mainBOB is running
    grepout = subprocess.check_output('ps -eo cmd | grep mainBOB.py | grep python3', stderr=subprocess.STDOUT, shell=True)
    grepout_str = grepout.decode('utf8', 'ignore')
    grepmatch = re.search(r'opt\/BOB\/mainBOB.py', grepout_str)
    return grepmatch

def ftpMINION():
    #ftp off minion log on cron job
    idBOB = getidforBOB()
    #copy minion file to unique file
    shutil.copy("/opt/BOB/logs/theminion.log", "/opt/BOB/logs/"+idBOB+"-theminion.log")
    try:
        minionwrite = f"lftp -c 'set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd BOB-update-log; glob -f --exist {idBOB}-theminion* && mput -e /opt/BOB/logs/{idBOB}-theminion.log; quit\" {speed2['host']}'"
        output = subprocess.check_output(minionwrite, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as lftpexc:
        if lftpexc.returncode == 1:
            minionup = f"lftp -c 'set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd BOB-update-log; mput /opt/BOB/logs/{idBOB}-theminion.log; quit\" {speed2['host']}'"
            output = subprocess.check_output(minionup, stderr=subprocess.STDOUT, shell=True)
        else:
            pass

def isminionDONE():
    #check to see if minion is done speed testing
    with open("/opt/BOB/logs/minionisdone.log", "w+") as minionFILE:
        readdoneness = minionFILE.read()
        #if extinct then send log last time and then write EXTINCTAGAIN! to done file
        if readdoneness == "EXTINCT!":
            ftpMINION()
            minionFILE.write("EXTINCTAGAIN!")
            minionFILE.close()
            #implement an erase through writing of the bobid log after upload right HERE!!!!
            shutil.copyfile("/opt/BOB/logs/theminion.log", f"/opt/BOB/logs/{idBOB}-theminion.log")
            sys.exit()
        elif readdoneness == "EXTINCTAGAIN!":
            #if EXINCTAGAIN log file is written, BOB is super done so exit
            minionFILE.close()
            sys.exit()
        else:
            pass

def main():
    #if minion is done do testing, do not reboot
    #so python checker exits here
    isminionDONE()
    #if minion is not done...
    #run search to see if mainBOB is running
    match = deploySEARCH()
    #send off the log and then reboot if needed
    logACTION(match)

if __name__ == '__main__':
    main()
