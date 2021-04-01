"""
author: kristine larson
called by quickLook_cl.py
quickLook functions - consolidated snr reader (previously in a separate file)
"""
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import subprocess

import scipy.interpolate
import scipy.signal

import gnssrefl.gps as g
import gnssrefl.rinex2snr as rinex


def read_snr_simple(obsfile):
    """
    author: Kristine Larson
    input: SNR observation filenames and a boolean for 
    whether you want just the first day (twoDays)
    output: contents of the SNR file, withe various other metrics
    """
#   defaults so all returned vectors have something stored in them
    sat=[]; ele =[]; azi = []; t=[]; edot=[]; s1=[];
    s2=[]; s5=[]; s6=[]; s7=[]; s8=[];
    snrE = np.array([False, True, True,False,False,True,True,True,True],dtype = bool)
#   
    allGood = 1
    try:
        f = np.genfromtxt(obsfile,comments='%')
        r,c = f.shape
        #print('read_snr_simple, Number of rows:', r, ' Number of columns:',c)
        sat = f[:,0]; ele = f[:,1]; azi = f[:,2]; t =  f[:,3]
        edot =  f[:,4]; s1 = f[:,6]; s2 = f[:,7]; s6 = f[:,5]
        s1 = np.power(10,(s1/20))  
        s2 = np.power(10,(s2/20))  
        s6 = s6/20; s6 = np.power(10,s6)  
#   make sure s5 has default value?
        s5 = []
        if c > 8:
            s5 = f[:,8]
            if (sum(s5) > 0):
                s5 = s5/20; s5 = np.power(10,s5)  
            #print(len(s5))
        if c > 9:
            s7 = f[:,9]
            if (sum(s7) > 0):
                s7 = np.power(10,(s7/20))  
            else:
                s7 = []
        if c > 10:
            s8 = f[:,10]
            if (sum(s8) > 0):
                s8 = np.power(10,(s8/20))  
            else:
                s8 = []
        if (np.sum(s5) == 0):
            snrE[5] = False; #print('no s5 data')
        if (np.sum(s6) == 0):
            #print('no s6 data'); 
            snrE[6] = False
        if (np.sum(s7) == 0):
           # print('no s7 data'); 
            snrE[7] = False
        if (np.sum(s8) == 0):
            snrE[8] = False; # print('no s8 data')
    except:
        print('problem reading the SNR file')
        allGood = 0
    return allGood, sat, ele, azi, t, edot, s1, s2, s5, s6, s7, s8, snrE


def quickLook_function(station, year, doy, snr_type,f,e1,e2,minH,maxH,reqAmp,pele,satsel,PkNoise,fortran,pltscreen):
    """
    inputs:
    station name (4 char), year, day of year
    snr_type is the file extension (i.e. 99, 66 etc)
    f is frequency (1, 2, 5), etc
    e1 and e2 are the elevation angle limits in degrees for the LSP
    minH and maxH are the allowed LSP limits in meters
    reqAmp is LSP amplitude significance criterion
    pele is the elevation angle limits for the polynomial removal.  units: degrees
    KL 20may10 pk2noise value is now sent from main function, which can be set online
    KL 20aug07 added fortran boolean
    KL 21feb06 return data from the plots so that Jupyter notebooks can use them.
    also added pltscreen variable so that the default plots are not always displayed
    KL 21mar25 added datakey dictionaries for the Jupyter notebook people
    """

    # dictionary for output
    data = {'NW':{},'SW':{},'NE':{},'SE':{},'fNW':{},'fSW':{},'fNE':{},'fSE': {} }

    # dictionary for key
    datakey = {'NW':{},'SW':{},'NE':{},'SE':{},'fNW':{},'fSW':{},'fNE':{},'fSE': {} }

    # make sure environment variables exist
    g.check_environ_variables()

    # make sure logs directory exists
    if not os.path.isdir('logs'):
        subprocess.call(['mkdir', 'logs'])

    webapp = False 
    # orbit directories
    ann = g.make_nav_dirs(year)
    # titles in 4 quadrants - for webApp
    titles = ['Northwest', 'Southwest','Northeast', 'Southeast']
    stitles = ['NW', 'SW','NE', 'SE']
    # define where the axes are located
    bx = [0,1,0,1]; by = [0,0,1,1]; bz = [1,3,2,4]

    # various defaults - ones the user doesn't change in this quick Look code
    delTmax = 70
    polyV = 4 # polynomial order for the direct signal
    desiredP = 0.01 # 1 cm precision
    ediff = 2 # this is a QC value, eliminates small arcs
    #four_in_one = True # put the plots together
    minNumPts = 20 
    #noise region for LSP QC. these are meters
    NReg = [minH, maxH]
    #print('Refl. Ht. Noise Region used: ', NReg)
    # for quickLook, we use the four geographic quadrants - these are azimuth angles in degrees
    azval = [270, 360, 180, 270, 0, 90, 90, 180]
    naz = int(len(azval)/2) # number of azimuth pairs
    pltname = 'temp.png' # default plot
    requireAmp = reqAmp[0]
    screenstats = True

# to avoid having to do all the indenting over again
# this allows snr file to live in main directory
# not sure that that is all that useful as I never let that happen
    obsfile = g.define_quick_filename(station,year,doy,snr_type)
    if os.path.isfile(obsfile):
        print('>>>> The snr file exists ',obsfile)
    else:
        if True:
            #print('looking for the SNR file on disk')
            obsfile, obsfileCmp, snre =  g.define_and_xz_snr(station,year,doy,snr_type)
            if snre:
                dkfjaklj = True
                #print('file exists on disk')
            else:
                print('>>>> The SNR the file does not exist ',obsfile)
                print('This code used to try and make one for you, but I have removed this option.')
                print('Please us rinex2snr and make a SNR file')
                sys.exit()
    allGood,sat,ele,azi,t,edot,s1,s2,s5,s6,s7,s8,snrE = read_snr_simple(obsfile)
    if allGood == 1:
        # make output file for the quickLook RRH values, just so you can give them a quick look see
        quicklog = 'logs/rh' + station + '.txt'
        rhout = open(quicklog,'w+')
        amax = 0
        minEdataset = np.min(ele)
        print('minimum elevation angle (degrees) for this dataset: ', minEdataset)
        if minEdataset > (e1+0.5):
            print('It looks like the receiver had an elevation mask')
            e1 = minEdataset
        if pltscreen:
            plt.figure(figsize=(10,6))
        for a in range(naz):
            if pltscreen:
                plt.subplot(2,2,bz[a])
                plt.title(titles[a])
            az1 = azval[(a*2)] ; az2 = azval[(a*2 + 1)]
            # this means no satellite list was given, so get them all
            if satsel == None:
                #satlist = g.find_satlist(f,snrE)
                #march 29, 2021 made l2c and l5 time dependent
                satlist = g.find_satlist_wdate(f,snrE,year,doy)
            else:
                satlist = [satsel]

            for satNu in satlist:
                x,y,Nv,cf,UTCtime,avgAzim,avgEdot,Edot2,delT= g.window_data(s1,s2,s5,s6,s7,s8,sat,ele,azi,t,edot,f,az1,az2,e1,e2,satNu,polyV,pele,screenstats) 
                if Nv > minNumPts:
                    maxF, maxAmp, eminObs, emaxObs,riseSet,px,pz= g.strip_compute(x,y,cf,maxH,desiredP,polyV,minH) 
                    nij =   pz[(px > NReg[0]) & (px < NReg[1])]
                    Noise = 0
                    iAzim = int(avgAzim)
                    if (len(nij) > 0):
                        Noise = np.mean(nij)
                    else:
                        Noise = 1; iAzim = 0 # made up numbers
                    if (delT < delTmax) & (eminObs < (e1 + ediff)) & (emaxObs > (e2 - ediff)) & (maxAmp > requireAmp) & (maxAmp/Noise > PkNoise):
                        T = g.nicerTime(UTCtime)
                        # az, RH, sat, amp, peak2noise, Time
                        rhout.write('{0:3.0f} {1:6.3f} {2:3.0f} {3:4.1f} {4:3.1f} {5:6.2f} {6:2.0f} \n '.format(iAzim,maxF,satNu,maxAmp,maxAmp/Noise,UTCtime,1))
                        if pltscreen:
                            plt.plot(px,pz,linewidth=1.5)
                        idc = stitles[a]
                        data[idc][satNu] = [px,pz]
                        datakey[idc][satNu] = [avgAzim, maxF, satNu,f,maxAmp,maxAmp/Noise, UTCtime]

                    else:
                        # these are failed tracks
                        if pltscreen:
                            plt.plot(px,pz,'gray',linewidth=0.5)
                        idc = 'f' + stitles[a]
                        data[idc][satNu] = [px,pz]
                        datakey[idc][satNu] = [avgAzim, maxF, satNu,f,maxAmp,maxAmp/Noise, UTCtime]
                        rhout.write('{0:3.0f} {1:6.3f} {2:3.0f} {3:4.1f} {4:3.1f} {5:6.2f} {6:2.0f} \n '.format(iAzim,maxF,satNu,maxAmp,maxAmp/Noise,UTCtime,-1))

            # i do not know how to add a grid using these version of matplotlib
            tt = 'GNSS-IR results: ' + station.upper() + ' Freq:' + g.ftitle(f) + ' Year/DOY:' + str(year) + ',' + str(doy)
            if pltscreen:
                aaa, bbb = plt.ylim()
                amax = max(amax,  bbb) # do not know how to implement this ...
                if (a == 3) or (a==1):
                    plt.xlabel('reflector height (m)')
                if (a == 1) or (a==0):
                    plt.ylabel('volts/volts')

        rhout.close()
        #print('preliminary reflector height results are stored in a file called logs/rh.txt')
        # do not plot if sending data to Jupyter Notebooks


        if pltscreen:
            plt.suptitle(tt, fontsize=12)
            # sure - throw in another plot
            goodbad(quicklog,station)
            plt.show()
          
    else: 
        print('some kind of problem with SNR file, so I am exiting the code politely.')


    # returns multidimensional dictionary of lomb scargle results so 
    # that the jupyter notebook people can replot them
    # 21mar26 added a key
    return data,datakey

def goodbad(fname,station):
    """
    simple visualizer of "good" and "bad" azimuths
    input is a filename and the station name
    """
    a = np.loadtxt(fname,comments='%')
    ij = (a[:,6] == 1) # good retrievals
    ik = (a[:,6] == -1) # bad retrievals
    plt.figure(figsize=(10,6))
    plt.subplot(3,1,1)
    plt.plot(a[ij,0], a[ij,1], 'o',color='blue',label='good')
    plt.plot(a[ik,0], a[ik,1], 'o',color='gray', label='bad')
    plt.title('quickLook Retrieval Metrics: ' + station)
    plt.legend(loc="upper right")
    plt.ylabel('reflector ht (m)')
    plt.grid()
    plt.xlim((0, 360))
    ax = plt.gca()
    ax.axes.xaxis.set_ticklabels([])


    plt.subplot(3,1,2)
    plt.plot(a[ij,0], a[ij,4], 'o',color='blue',label='good')
    plt.plot(a[ik,0], a[ik,4], 'o',color='gray', label='bad')
    plt.ylabel('peak2noise')
    plt.grid()
    plt.xlim((0, 360))
    ax = plt.gca()
    ax.axes.xaxis.set_ticklabels([])

    plt.subplot(3,1,3)
    plt.plot(a[ij,0], a[ij,3], 'o',color='blue',label='good')
    plt.plot(a[ik,0], a[ik,3], 'o',color='gray', label='bad')
    plt.ylabel('spectral peak amplitude')
    plt.xlabel('Azimuth (degrees)')
    plt.grid()
    plt.xlim((0, 360))

# old code
#print('I will try to pick up a RINEX file ')
#print('and translate it for you. This will be GPS only.')
#print('For now I will check all the official archives for you.')
#rate = 'low'; dec_rate = 0; archive = 'all'; 
#rinex.conv2snr(year, doy, station, int(snr_type), 'nav',rate,dec_rate,archive,fortran)
#if os.path.isfile(obsfile):
#    print('the SNR file now exists')  
#else:
#    print('the RINEX file did not exist, had no SNR data, or failed to convert, so exiting.')
