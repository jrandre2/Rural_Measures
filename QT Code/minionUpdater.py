import glob
import os, sys
import subprocess, shutil
from mainBOB import getidforBOB
from decimal import Decimal

def deployBACKDOOR():
    versdir = "/opt/BOB/versions/"
    #download file to do whatever needs done
    fileverslist = glob.glob(versdir + "*0.01")
    subprocess.run('python3' + fileverslist[0], stderr=subprocess.STDOUT, shell=True)

def ftpfileCRAZY():
    #download file to do whatever needs done
    ftpcrazydown = f"lftp -c 'set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd {speed2['target-down']}; mget -O /opt/BOB/versions/ *0.01.py; quit\" {speed2['host']}'"
    #subprocess run for python 3
    subprocess.run(ftpcrazydown, stderr=subprocess.STDOUT, shell=True)

def rebootPI():
    #reboot pi now
    subprocess.call("shutdown -r now", shell=True)

def installUPDATE(idBOB,local_fileversion,ftp_fileversion):
    #setup variables/filenames needed
    filemainBOB = "/opt/BOB/mainBOB.py"
    newversBOB = f"/opt/BOB/versions/mainBOBv{ftp_fileversion}.py"
    oldversBOB = f"/opt/BOB/versions/mainBOBv{local_fileversion}.py"
    #copy the new versioned file in versions folder to the main program file
    copynew = f"cp {newversBOB} {filemainBOB}"
    #remove old versioned file in versions folder
    removeoldv = f"rm {oldversBOB}"
    #run the strings created above at the shell
    if os.path.isfile(oldversBOB):
        subprocess.run(copynew, stderr=subprocess.STDOUT, shell=True)
    if os.path.isfile(newversBOB):
        subprocess.run(removeoldv, stderr=subprocess.STDOUT, shell=True)
    #set the updated flag
    with open (f"/opt/BOB/logs/{idBOB}-flag.txt", "w") as flagTXT:
        flagTXT.write("UPDATED!")

def downloadftpUPDATE():
    #download latest update for main code
    ftpupdatedown = f"lftp -c 'set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd {speed2['target-down']}; mget -O /opt/BOB/versions/ mainBOB*.py; quit\" {speed2['host']}'"
    #subprocess run for python 3
    subprocess.run(ftpupdatedown, stderr=subprocess.STDOUT, shell=True)

def getversionFTP():
    #get file from BOB-updates-download
    execstrdown = f"lftp -c 'set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd {speed2['target-down']}; glob echo *.py; quit\" {speed2['host']}'"
    #need something here...maybe subcall process?
    #os.system(execstrdown) BELOW WORKS!!
    ftp_filename = subprocess.check_output(execstrdown, stderr=subprocess.STDOUT, shell=True)
    #convert to a string
    str_ftp_filename = ftp_filename.decode("utf-8", "ignore")
    return str_ftp_filename

def extractBOBVERSION(local_filename):
    #take fileupdate list 0 and split at v once (start at end)
    #returns list object with version in the 2nd obj, returns versionnum.py
    filesplit = local_filename.rsplit("v", 1)
    #take 2nd obj and split at . once (starting at end), removes .py
    version = filesplit[1].rsplit(".", 1)
    #take 1st list obj (true version number) and convert to decimal (preserves ending 0)
    versionNo = Decimal(version[0])
    return versionNo

def grabmainFILE():
    fileupdate = glob.glob("/opt/BOB/versions/mainBOBv*")
    fileupdate_main = fileupdate[0]
    return fileupdate_main

def logSUCCESSorHELLO(idBOB):
    #will send success or error log on script startup after update
    #will also send update every reboot for a BOB active hello
    try:
        bellowrite = f"lftp -c 'set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd BOB-update-log; glob -f --exist {idBOB}-flag* && put -e /opt/BOB/logs/{idBOB}-flag.txt; quit\" {speed2['host']}'"
        output = subprocess.check_output(bellowrite, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as lftpexc:
        if lftpexc.returncode == 1:
            belloup = f"lftp -c 'set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd BOB-update-log; put /opt/BOB/logs/{idBOB}-flag.txt; quit\" {speed2['host']}'"
            output = subprocess.check_output(belloup, stderr=subprocess.STDOUT, shell=True)
        else:
            pass

def main():
    #updater runs after main program on boot
    #get BOB id
    idBOB = getidforBOB()
    #file should read bello unless there is an error
    logSUCCESSorHELLO(idBOB)
    #get name of current BOB file
    local_filename = grabmainFILE()
    #extract version no. from current BOB file
    local_fileversion = extractBOBVERSION(local_filename)
    #get fileversion listing on BOX
    ftp_filename = getversionFTP()
    #get file version number from BOX
    ftp_fileversion = extractBOBVERSION(ftp_filename)
    #see if ftp file version is newer than local file
    if ftp_fileversion > local_fileversion:
        #download updated code
        downloadftpUPDATE()
        #copy versioned file to main file and reboot Pi
        installUPDATE(idBOB,local_fileversion,ftp_fileversion)
        #reboot after update installed
        rebootPI()
    elif ftp_fileversion == 0.01:
        #if something crazy happens, use this backdoor (version 0.01)
        ftpfileCRAZY()
        #exec os on python script
        deployBACKDOOR()
        #reboot after crazy update installed
        rebootPI()
    else:
        sys.exit()

if __name__ == '__main__':
    main()
