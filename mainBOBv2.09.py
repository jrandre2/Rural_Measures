import logging
import speedtest
from driver import apa102
import datetime, time
import os, sys, subprocess, shutil
import serial
from serial import SerialException
import requests
# requests package built on top of urllib3
import urllib3
import csv
import pytz
import glob

#VERSION 2.08. RUN CRAY-CRAY UPDATE!

#Usually RP2, but disabled bt so AMA0 could be used
#Need AMA0 as it's faster, higher throughput, less errors
port = "/dev/ttyAMA0"  # Raspberry Pi 2
#port = "/dev/ttyS0"    # Raspberry Pi 3

#define LEDs for led lights = 2
#config for crossover wiring: mosi=11 & slck=10 (straight through is mosi=10 & sclk=11)
hatleds = apa102.APA102(num_led=2, global_brightness=20, mosi=11, sclk=10, order='rgb')

#REMOVE IN FUTURE VERSIONS
def runCRAYCRAY():
    #only upgrade and reboot if speedtest is 2.1.1
    result = subprocess.run('speedtest-cli --version', stdout=subprocess.PIPE, shell=True)
    result2 = result.stdout.decode('utf-8')
    if "speedtest-cli 2.1.1" in result2:
        subprocess.run('sudo pip3 install speedtest-cli --upgrade', stderr=subprocess.STDOUT, shell=True)
        rebootPI()

def bluelightMINION():
    #clear strip to reset color
    hatleds.clear_strip()
    #set both LEDs to blue
    hatleds.set_pixel_rgb(0, 0x0000FF)
    hatleds.set_pixel_rgb(1, 0x0000FF)
    #show the lights
    hatleds.show()

def cleanupdataBOB():
    cleanuplist = glob.glob("/opt/BOB/data/*.*")
    for f in cleanuplist:
        os.remove(f)
    logging.warning('Minion is cleaning up your csv mess in data folder.')

def extinctBOB(idBOB):
    #LAST LOGS HERE!!!! LOG FILE OVERWRITE!!!
    logging.warning('BOB was marked as EXTINCT!')
    #copy over the log file ONE LAST TIME for upload by pythonChecker
    shutil.copyfile("/opt/BOB/logs/theminion.log", "/opt/BOB/logs/"+idBOB+"-theminion.log")
    #tell pythonChecker that BOB is extinct by OVERWRITING minion is done log
    #pythonChecker will upload id log one last time and delete
    with open("/opt/BOB/logs/minionisdone.log", "r+") as minionFILE:
        minionFILE.seek(0)
        minionFILE.truncate()
        minionFILE.write("EXTINCT!")
        minionFILE.close()

def uploaddeactiveBOB(idBOB):
    try:
        #overwrite activated BOB file locally
        with open(f"/opt/BOB/data/activate-{idBOB}.txt", "r+") as deactivateFILE:
            deactivateFILE.seek(0)
            deactivateFILE.truncate()
            #write deactivate BOB style
            deactivateFILE.write("BOB SAYS DEACTIVATE!!!")
    except OSError as e:
        logging.warning(f"BOB local deactivate file not found. Creating one to upload.")
        with open(f"/opt/BOB/data/activate-{idBOB}.txt", "w+") as deactivateFILE:
            deactivateFILE.write("BOB SAYS DEACTIVATE!!!")
    #make deactivate file FTP string to upload deactivated file
    deactivateBOBstr = f"lftp -c 'set net:timeout 10; set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd {speed2['target-activate']}; glob -f --exist activate-{idBOB}*  && mput -e /opt/BOB/data/activate-{idBOB}*; quit\" {speed2['host']}'"
    #check output of subprocess; if file doesn't exist, error code = 1 and it throws exception
    #if file does exist, no exception so delete target file and mput new
    try:
        output = subprocess.check_output(deactivateBOBstr, stderr=subprocess.STDOUT, shell=True)
        logging.warning('BOB deactivated')
    except subprocess.CalledProcessError as lftpexc:
        logging.warning('BOB was NOT deactivated. Manually check. Activate file does not exist on BOX.')

def copyfileGPS(idBOB,pubIP):
    shutil.copyfile("/opt/BOB/data/"+idBOB+"-GPSbello.csv","/opt/BOB/data/"+pubIP+"-"+idBOB+"-GPSfinal.csv")
    logging.warning('Copying unique GPS file')

def writeINTROW(pubIP,idBOB,speedstuff):
    #use csv read/writer
    with open ('/opt/BOB/data/'+pubIP+'-'+idBOB+'-speed.csv','a') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(speedstuff)
        logging.warning(f'Speedtest successful, writing row!{speedstuff}')

def verifyINTCSV(pubIP,idBOB):
    #if file exists, count lines and return
    #if file does not exist, create, open and write header
    rowCOUNT = 0
    try:
        with open ('/opt/BOB/data/'+pubIP+'-'+idBOB+'-speed.csv', 'r') as csvFile:
            rowCOUNT = sum(1 for row in csvFile)
            logging.warning(f'Counting rows in Internet CSV = {rowCOUNT}.')
            return rowCOUNT
    except FileNotFoundError:
        with open ('/opt/BOB/data/'+pubIP+'-'+idBOB+'-speed.csv','w') as csvFile:
            writer = csv.writer(csvFile, delimiter = ',', lineterminator= '\n',)
            writer.writerow(['current time', 'download', 'upload', 'ping', 'ISP name', 'IP address'])
            logging.warning('Setup CSV for Internet.')
            return rowCOUNT

def doSPEEDTEST():
    #create test var for speedtest and then get best server (closest) & test up/down
    try:
        test = speedtest.Speedtest()
    except Exception:
        logging.exception("Error in speedtest")
        time.sleep(300)
        return [0, 0, 0, 0, 0, 0];
    else:
        test.get_servers()
        test.get_best_server()
        test.download()
        test.upload()
        #grab results in dict format
        testres = test.results.dict()
        #parse out ip and isp in client dict obj
        user = testres["client"]
        #change to float and convert bits to mbps
        down = float(testres["download"])
        user_down = down / (1048576)
        up = float(testres["upload"])
        #1024 * 1024 = 1048576. Divide by 1024 twice (bits to mbps)
        user_up = up / (1048576)
        user_ping = float(testres["ping"])
        #user_time = testres["timestamp"]
        #server time here was inaccurate
        user_isp = str(user['isp'])
        user_ip = str(user['ip'])
        cent_zone = pytz.timezone('America/Chicago')
        cent_time = datetime.datetime.now(tz=cent_zone)
        return [cent_time, user_down, user_up, user_ping, user_isp, user_ip];

def intledGREEN():
    #clear strip and set internet to green
    hatleds.clear_strip()
    #set 0 or GPS to red
    hatleds.set_pixel_rgb(0, 0xFF0000)
    #set 1 or Internet to green
    hatleds.set_pixel_rgb(1, 0x00FF00)
    #show new colors
    hatleds.show()
    logging.warning('Internet LED GREEN!')

def closeGPS(serialGPS):
    serialGPS.close()

def ftpstoBOX(upfile):
    #make string so if file exists, delete it and then upload
    delupfile = f"lftp -c 'set net:timeout 10; set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd {speed2['target-up']}; glob -f --exist {upfile}*  && mput -e /opt/BOB/data/{upfile}*; quit\" {speed2['host']}'"
    #on exception, file does not exist so just upload
    makenewfile = f"lftp -c 'set net:timeout 10; set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd {speed2['target-up']}; mput /opt/BOB/data/{upfile}*; quit\" {speed2['host']}'"
    #check output of subprocess; if file doesn't exist, error code = 1 and it throws exception
    #if file does exist, no exception so delete target file and mput new
    try:
        output = subprocess.check_output(delupfile, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as lftpexc:
        if lftpexc.returncode == 1:
            output = subprocess.check_output(makenewfile, stderr=subprocess.STDOUT, shell=True)
        else:
            pass

def writeGPSROW(pubIP,idBOB,GPSdata):
    #use csv read/writer
    with open ('/opt/BOB/data/'+pubIP+'-'+idBOB+'-GPSfinal.csv','a') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(GPSdata)
        logging.warning(f'Writing GPS data: {GPSdata}')

def setupGPSCSV(pubIP,idBOB):
    #if file exists, count lines and return
    #if file does not exist, create, open and write header
    rowCOUNT = 0
    try:
        with open ('/opt/BOB/data/'+pubIP+'-'+idBOB+'-GPSfinal.csv', 'r') as csvFile:
            rowCOUNT = sum(1 for row in csvFile)
            logging.warning('Counting rows in GPS CSV')
            return rowCOUNT
    except FileNotFoundError:
        with open ('/opt/BOB/data/'+pubIP+'-'+idBOB+'-GPSfinal.csv','w') as csvFile:
            writer = csv.writer(csvFile, delimiter = ',', lineterminator= '\n',)
            writer.writerow(['time','latitude', 'longitude'])
            logging.warning('Creating GPS CSV')
            return rowCOUNT

def gpsledGREEN():
    #clear strip and set gps to green
    hatleds.clear_strip()
    #set 0 or GPS to green
    hatleds.set_pixel_rgb(0, 0x00FF00)
    #set 1 or Internet to green, too. Already tested.
    hatleds.set_pixel_rgb(1, 0x00FF00)
    #show new colors
    hatleds.show()
    logging.warning('GPS LED GREEN!')

#called from readyGPS()
#parseGPS grabs GPS coordinates in proper format
def parseGPS(data):
    #get gpgga string where lat and long exist
    if "$GPGGA" in data:
        gps_string = data.split(",")
        #make sure lat is a float, otherwise keep trying to get good data
        try:
            float(gps_string[2])
        except Exception:
            logging.error("Bad data in lat:" + gps_string[2])
            return 0
        else:
            lat = decodeGPS(gps_string[2])
            if "S" in gps_string[3]:
                lat = "-" + str(lat)
        #make sure long is a float, otherwise keep trying to get good data
        try:
            float(gps_string[4])
        except Exception:
            logging.error("Bad data in long:" + gps_string[4])
            return 0
        else:
            lon = decodeGPS(gps_string[4])
            if "W" in gps_string[5]:
                lon = "-" + str(lon)
        gpszone = pytz.timezone('America/Chicago')
        gpstime = datetime.datetime.now(tz=gpszone)
        return [gpstime, lat, lon];
    else:
        return 0
#called from parseGPS()
#formats lat / long from NMEA to decimal
def decodeGPS(coord):
    # DDDMM.MMMMM -> DD deg MM.MMMMM min
    v = coord.split(".")
    #head is DDDMM
    head = v[0]
    #tail is MMMMMMM
    tail =  v[1]
    #deg is 0 in front and -2 in back
    deg = head[0:-2]
    #min is the -2 in back plus a decimal and then the tail
    min = head[-2:] + "." + tail
    #convert to a float from a string
    float_min = float(min)
    #divide MM.MMMMMM by 60 for true decimal form
    conv_min = float_min / 60
    #convert degrees to an integer
    conv_deg = int(deg)
    #add the degrees and minutes together (i.e. 40 + 0.8276)
    GPS_DD_MM = conv_deg + conv_min
    return GPS_DD_MM

def readyGPS(ser):
    #gps counter for loop
    gps_i = 0
    #loop through 100 times max to lock on to GPS and find correct GP string
    #if more than 100, assume cannot get GPS
    while gps_i < 50:
        data = ser.readline().decode('utf-8', 'ignore')
        #parse the data out so it's readable
        GPSdata = parseGPS(data)
        gps_i +=1
        #make sure GPS data is ready and not zeroes
        if GPSdata != 0:
            return GPSdata
        elif gps_i == 49:
            #if the counter = 49, GPS is getting 0 data
            #if this happens, sleep for 5 secs and return unavailable to main loop
            time.sleep(5)
            GPSdata = ["GPS cannot lock", "and is", "unavailable!!!"]
            logging.error('GPS getting 0 data')
            return GPSdata

def openGPS():
    #port is defined up top as global var tty serial0
    try:
        ser = serial.Serial(port, baudrate = 9600, timeout = 1)
    except (SerialException, IOError):
        ser.close()
        logging.error('Could not open serial connection')
        return 0
    else:
        return ser

def checkifactiveBOB(idBOB):
    #check local downloaded file for activation
    with open(f"/opt/BOB/data/activate-{idBOB}.txt", "r") as activationFILE:
        readActivation = activationFILE.read()
        if readActivation == "activated":
            activationFILE.close()
            logging.warning('BOB is activated.')
        else:
            activationFILE.close()
            logging.warning('BOB is NOT activated. Check file name or read activation code.')
            sys.exit()

def downloadactiveBOB(idBOB):
    #download activation file from BOX
    try:
        putfile = f"lftp -c 'set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd {speed2['target-activate']}; mget -e activate-{idBOB}* -O /opt/BOB/data; quit\" {speed2['host']}'"
        output = subprocess.check_output(putfile, stderr=subprocess.STDOUT, shell=True)
    #if the file does not exist locally, then get without the -e flag
    except subprocess.CalledProcessError as lftpexc:
        if lftpexc.returncode == 1:
            putfile2 = f"lftp -c 'set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd {speed2['target-activate']}; mget activate-{idBOB}* -O /opt/BOB/data; quit\" {speed2['host']}'"
            output2 = subprocess.check_output(putfile2, stderr=subprocess.STDOUT, shell=True)
        else:
            logging.error(f'Unknown error during ftp get of activation file on BOX')
            sys.exit()

def checkactivationfileBOX(idBOB):
    #failsafe in case of user data entry on BOX
    try:
        existingfile = f"lftp -c 'set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd {speed2['target-activate']}; glob -f --exist activate-{idBOB}*; quit\" {speed2['host']}'"
        output = subprocess.check_output(existingfile, stderr=subprocess.STDOUT, shell=True)
    #if the file does not exist on FTP, then log the error and exit program
    except subprocess.CalledProcessError:
        logging.error(f'No activation file available for {idBOB}! on BOX!')
        sys.exit()

def setaliveBOB(idBOB):
    try:
        #set minionisdone to alive so pythonChecker knows BOB is alive and not extinct
        with open ("/opt/BOB/logs/minionisdone.log", "r+") as aliveTXT:
            aliveTXT.seek(0)
            aliveTXT.truncate()
            aliveTXT.write("ALIVE!")
            aliveTXT.close()
    except IOError:
        pass

def checkandsetFLAGS(idBOB):
    try:
    #check for update, if update then log to log file
        with open (f"/opt/BOB/logs/{idBOB}-flag.txt", "w+") as rflagTXT:
            updaterFILE = rflagTXT.read()
            if updaterFILE == "UPDATED!":
                logging.warning("BOB has been updated")
                rflagTXT.close()
            else:
                rflagTXT.seek(0)
                rflagTXT.truncate()
                rflagTXT.write("ALIVE!")
                rflagTXT.close()
    except IOError:
        pass

def isspeedfileonBOX(upfile):
    #is speed file already on BOX?
    existingfile = f"lftp -c 'set net:timeout 10; set ftp:ssl-allow true; set ssl:check-hostname no; open -u {speed2['user']},{speed2['pass']} -e \"cd {speed2['target-up']}; glob -f --exist {upfile}*; quit\" {speed2['host']}'"
    #if file does exist, return 1 and exit
    #on exception, file does not exist, return 0 and exit
    fileEXISTS = 1
    try:
        output = subprocess.check_output(existingfile, stderr=subprocess.STDOUT, shell=True)
        return fileEXISTS
    except subprocess.CalledProcessError as lftpexc:
        if lftpexc.returncode == 1:
            fileEXISTS = 0
            return fileEXISTS

def getpublicIP():
    #get public IP through IPify.org
    for url in ['http://api.ipify.org']:
        try:
            ipaddress = requests.get(url, timeout=3).text
            logging.error(f'IP address successful')
            return ipaddress
        except (requests.ConnectionError, urllib3.exceptions.ReadTimeoutError) as e:
            logging.exception('Cannot get public IP')
            return 0

def readyINTERNET():
    #try accessing google.com for 3 seconds
    #if success, return 1; if fails, return 0
    for url in ['http://google.com']:
        try:
            urlresponsecode = requests.get(url, timeout=3)
            return 1
        except requests.ConnectionError:
            logging.exception('Internet connection error occurred')
            return 0

def checkINTERNET():
    #initialize sleep
    intSLEEP = 1
    #check for Internet; if not ready, try 10 times to see if it will be ready
    for i in range(0, 10): #try 10 times
        interwebs = readyINTERNET()
        #if interwebs = 0 internet is not available, sleep and try again
        if interwebs == 0:
            time.sleep(intSLEEP)
            intSLEEP *= 2 #backoff alg here to increment sleep through iteration
        else:
            break #if no error, Internet is good so break out of loop
        #
        #if count reaches 9, Internet is not plugged in or broken
        #reboot and try again
        if i == 9:
            logging.error("Internet connection broken. Needs plugged in.")
            rebootPI()

def getidforBOB():
    #get id for BOB from cpuinfo file
    #https://www.raspberrypi-spy.co.uk/2012/09/getting-your-raspberry-pi-serial-number-using-python/
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo','r')
        for line in f:
            if line[0:6]=='Serial':
                cpuserial = line[18:26]
        f.close()
    except:
        cpuserial = "ERROR000000000"
        logging.error('Cannot get CPU ID on this BOB')
        return cpuserial
    return cpuserial

def rebootPI():
    #reboot pi now
    subprocess.call("shutdown -r now", shell=True)

def readyredLEDS():
    #clear strip to black
    hatleds.clear_strip()
    #set both LEDs to red
    hatleds.set_pixel_rgb(0, 0xFF0000)
    hatleds.set_pixel_rgb(1, 0xFF0000)
    #show the color
    hatleds.show()
    logging.warning('BOB starting up. LEDs RED!')

#######################################################
##########       MAIN      ############################
#######################################################

def main():
    #make logfile
    logging.basicConfig(filename='/opt/BOB/logs/theminion.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logging.warning('START OF LOGGING')
    #remove on next update
    runCRAYCRAY()
    #make leds red
    readyredLEDS()
    #######################################################
    ########    INITIALIZE    #############################
    #######################################################
    #get BOB id to use for GPS & Internet
    idBOB = getidforBOB()
    #make sure Internet is up and ready
    checkINTERNET()
    #turn Internet LED green
    intledGREEN()
    #when Internet is ready, get public IP
    pubIP = getpublicIP()
    #if pubIP is 0, reboot and try again; there is nothing to do until pubIP works
    if pubIP == 0:
        rebootPI()
    #set speed count and end for main loop to zero
    speedCOUNT = 0
    theendORNOT = 0
    #set speed file variable to transfer data
    speedFILE = f"{pubIP}-{idBOB}-speed"
    #######################################################
    ########     NEW BOB     ##############################
    #######################################################
    #setup csv parameters (open file, name file, make headings)
    #if file exists, count rows and make speed counter start at a higher number
    #more interested in speed than gps, so check for speed first
    int_rowCOUNT = verifyINTCSV(pubIP,idBOB)
    if int_rowCOUNT != 0:
        speedCOUNT = int_rowCOUNT
    #if rowCOUNT is 1 or 0, makes sure it's a new reading and not an unplug/replug
    #on blue lights incident; speed file should only start uploading after 10 rows.
    if int_rowCOUNT <= 1:
        theendORNOT = isspeedfileonBOX(speedFILE)
    #
    #only loop through if speed file does not already exist
    #if it does exist, goes to cleanup, blue lights and exit
    if theendORNOT == 0:
        #used after updating to check script start and log update
        checkandsetFLAGS(idBOB)
        #set BOB to alive so pythonChecker reboots if needed
        setaliveBOB(idBOB)
        #check BOX for activation file (just in case)
        checkactivationfileBOX(idBOB)
        #download FTP file for activation for BOB
        downloadactiveBOB(idBOB)
        #check FTP file for activation
        #if not active, program exits
        checkifactiveBOB(idBOB)
        #
        #######################################################
        ##########       GPS      #############################
        #######################################################
        #initialize sleep
        SLEEP = 20
        #open GPS connection and return serial data
        #try 5 times to open serial and then continue on
        for x in range(0, 4): #try 4 times
            serialGPS = openGPS()
            #if serialGPS = 0 an exception has occurred, sleep and try again
            if serialGPS == 0:
                time.sleep(SLEEP)
                SLEEP *= 2 #backoff alg here to increment sleep through iteration
            else:
                break #if no error, serial is opened and break out of loop

            #if count reaches 4, GPS hat may be broken
            if x == 3:
                logging.error("Serial connection broken. Possible repair needed.")
        #
        #after serial opened, turn GPS green
        #if never opens, turn green any way for user
        gpsledGREEN()
        #after GPS is opened without exception, take 50 readings
        gpsCOUNT = 0
        #setup csv parameters (open file, name file, make headings)
        #if file exists, count rows and make gps counter start at a higher number
        rowCOUNT = setupGPSCSV(pubIP,idBOB)
        if rowCOUNT != 0:
            gpsCOUNT = rowCOUNT
        #
        #loop through 50 GPS readings
        while gpsCOUNT < 51:
            #get correct GPS reading, make sure it's not zero and parse it
            GPSdata = readyGPS(serialGPS)
            writeGPSROW(pubIP,idBOB,GPSdata)
            gpsCOUNT += 1
        #close serial, done with this
        closeGPS(serialGPS)
        #ftp gps bello data
        gpsFILE = f"{pubIP}-{idBOB}-GPSfinal"
        ftpstoBOX(gpsFILE)
        logging.warning("Final GPS data is sent.")
        #
        #######################################################
        ##########    INTERNET    #############################
        #######################################################
        #loop through 2016 speedtest readings
        #SET TO 2017 +1 for heading
        while speedCOUNT < 1863:
            #when Internet is ready, do 1862 (266 per day for 7 days) readings
            #ftp readings after every ten readings (after 266 readings)
            if (((speedCOUNT - 1) % 10) == 0):
                ftpstoBOX(speedFILE)
                logging.warning('Internet data uploading...')
            speedstuff = doSPEEDTEST()
            writeINTROW(pubIP,idBOB,speedstuff)
            speedCOUNT += 1
            #sleep for 300 seconds = 5 minutes
            time.sleep(300)
        #copy gps to unique file
        #copyfileGPS(idBOB,pubIP)
        #ftp gps file as unique
        #gpsfinFILE = f"{pubIP}-{idBOB}-GPSfinal"
        #ftpstoBOX(gpsfinFILE)
        #ftp one last time to make sure everything uploaded
        ftpstoBOX(speedFILE)
        logging.warning('ALL FILES COMPLETE.')
        #######################################################
        ##########    CLEANUP IF TESTING     ##################
        #######################################################
        #write out that BOB is extinct for pythonChecker
        extinctBOB(idBOB)
    #######################################################
    ############  CLEANUP DATA & BLUE LIGHTS ##############
    #######################################################
    #if theendORNOT returns existing file, code should land here
    #upload file to deactivate the BOB
    #do this every time in case user hits blue lights but reactivates BOB
    uploaddeactiveBOB(idBOB)
    #delete CSVs and get ready for the next customer
    #need to do this because CSV gets created (headings)
    cleanupdataBOB()
    #make lights blue to indicate a done minion
    bluelightMINION()
    #after everything is done, exit!
    sys.exit()

if __name__ == '__main__':
        main()
