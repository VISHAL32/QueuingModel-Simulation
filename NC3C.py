#!/usr/bin/python3

import os
import sys
import random
import datetime
import simpy
import xlsxwriter

from simpy.core import Environment

"""
Setting variables
"""
global STATE, TEMP#, TC  #SUM_ALL,
STATE   = 0
TEMP    = 0
# SUM_ALL = 0.00
# TC = 0
CALC = [0] * 500   # Input capacity
TC = 0

# Simulation time in minutes
OPEN_TIME  = 7   # Morning
CLOSE_TIME = 21  # Night
START = OPEN_TIME*60
SIM_END = CLOSE_TIME*60

SIM_FACTOR = 1/60  # Simulation realtime factor
PEAK_START = 11
PEAK_END   = 13
PEAK_TIME  = 60*(PEAK_END-PEAK_START)  # Range of peak hours

NUM_COUNTERS = 3 # Number of counters in the drive-thru
# Minutes it takes in each counters
TIME_COUNTER_A = 3 #random.randint(1,3)
TIME_COUNTER_B = 2 #random.randint(1,3)
TIME_COUNTER_C = 1 #random.randint(1,3)

# Create a customer every [min, max] minutes
CUSTOMER_RANGE_NORM = [5, 10] # in normal hours
CUSTOMER_RANGE_PEAK = [1,5]  # in peak hours
CUSTOMER_RANGE = CUSTOMER_RANGE_NORM


#==============================================================================
"""
Defining Queue properties
"""
def toc(raw):
    clock = ('%02d:%02d' % (raw/60, raw%60))
    return clock

def cr(string):
    return "\033%s\033" % string

def cy(string):
    return "\033%s\033" % string

def cg(string):
    return "\033%s\033" % string

def cb(string):
    return "\033%s\033" % string

def cm(string):
    return "\033%s\033" % string

def cgray(string):
    return "\033%s\033" % string

global ic_in, ic_go, ic_lv, ic_info, ic_ask, ic_mon, ic_stop, ic_dang

ic_in   = cy("[waiting]")
ic_go   = cy("[checkout]")
ic_lv   = cy("[left]")
ic_info = cb("[i[information]")
ic_ask  = cm("[ask]")
ic_mon  = cg("[paid]")
ic_stop = cr("[hold]")
ic_dang = cr("[closed]")

#=============================================================================
"""
Waiting Lane
"""
class waitingLane(object):

    def __init__(self, env):
        self.env = env
        self.lane = simpy.Resource(env, 3)

    def serve(self, cust):
        yield self.env.timeout(0)
        # print("%s (%s) %s entered the area" % (ic_in, toc(env.now), cust))

#==============================================================================
"""
First counter class
"""
class giveOrder(object):

    def __init__(self, env):
        self.env = env
        self.employee = simpy.Resource(env, 1)

    def serve(self, cust):
        yield self.env.timeout(random.randint(TIME_COUNTER_A-1, TIME_COUNTER_A+1))
        # print("%s (%s) %s ordered the menu" % (ic_ask, toc(env.now), cust))

#==============================================================================
"""
Second counter class
"""
class payForOrder(object):

    def __init__(self, env):
        self.env = env
        self.employee = simpy.Resource(env, 1)

    def serve(self, cust):
        yield self.env.timeout(random.randint(TIME_COUNTER_B-1, TIME_COUNTER_B+1))
        # print("%s (%s) %s paid the order" % (ic_mon, toc(env.now), cust))

#==============================================================================
"""
Third counter class
"""
class takeawayOrder(object):

    def __init__(self, env):
        self.env = env
        self.employee = simpy.Resource(env, 1)

    def serve(self, cust):
        yield self.env.timeout(random.randint(TIME_COUNTER_C-1, TIME_COUNTER_C+1))
        # print("%s (%s) %s took the order" % (ic_stop, toc(env.now), cust))

#==============================================================================

"""
Define customer behavior at first counter
"""
def counterA(env, name, waiting, counter1, counter2, counter3):

    with waiting.lane.request() as request:

        if (env.now >= SIM_END):
            # print("%s Not enough time! %s cancelled" % (ic_dang, name))
            env.exit()

        yield request
        yield env.process(waiting.serve(name))
        # print("%s (%s) %s is in waiting lane" % (ic_in, toc(env.now), name))

    # Start the actual drive-thru process
    # print("At Counter [1] \n%s (%s) %s goes into drive-thru counter" % (ic_go, toc(env.now), name))

    with counter1.employee.request() as request:

        if (env.now + TIME_COUNTER_A >= SIM_END):
            # print("%s Not enough time! Assumed %s is quickly finished" % (ic_dang, name))
            yield env.timeout(0.5)
            env.exit()

        yield request

        CALC[int(name[5:])] = env.now
        yield env.process(counter1.serve(name))
        # print("%s (%s) %s choose the order" % (ic_ask, toc(env.now), name))

        # print("At Counter[2] \n (%s) %s will pay the order" % (toc(env.now), name))
        env.process(counterB(env, name, counter1, counter2, counter3))

"""
Define customer behavior at second counter
"""
def counterB(env, name, counter1, counter2, counter3):


    with counter2.employee.request() as request:

        if (env.now + TIME_COUNTER_B >= SIM_END):
            # print("%s Not enough time! Assumed %s is quickly finished" % (ic_dang, name))
            yield env.timeout(0.5)
            env.exit()

        yield request

        yield env.process(counter2.serve(name))
        # print("%s (%s) %s is paying the order" % (ic_mon, toc(env.now), name))

        # print("At Counter [3] \n (%s) %s will take the order" % (toc(env.now), name))
        env.process(counterC(env, name, counter1, counter2, counter3))
"""
Define customer behavior at third counter
"""
def counterC(env, name, counter1, counter2, counter3):

    with counter3.employee.request() as request:

        if (env.now + TIME_COUNTER_C >= SIM_END):
            # print("%s Not enough time! Assumed %s is quickly finished" % (ic_dang, name))
            yield env.timeout(0.5)
            env.exit()

        yield request

        yield env.process(counter3.serve(name))
        # print("%s (%s) %s leaves" % (ic_lv, toc(env.now), name))

        global TEMP
        TEMP = int(name[5:])
        CALC[int(name[5:])] = env.now - CALC[int(name[5:])]



#==============================================================================
"""
Default Environment with 3 counters
"""
def setupenv(env, cr):
    # Create all counters
    waiting  = waitingLane(env)
    counter1 = giveOrder(env)
    counter2 = payForOrder(env)
    counter3 = takeawayOrder(env)
    i = 0

    # Create more customers while the simulation is running
    while True:
        yield env.timeout(random.randint(*cr))
        i += 1
        env.process(counterA(env, "Cust %d" % i, waiting, counter1, counter2, counter3))

#==============================================================================
"""
main program
"""
if __name__ == "__main__":

    # f = open('output.txt', 'a')
    workbook = xlsxwriter.Workbook('NC3C.xlsx')
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, "Total Hours:")
    worksheet.write(0, 1, "Total Coustomers:")
    worksheet.write(0, 3, "Average Service time:")
    row = 1
    for i in range(0, 1000):

            os.system(['clear','cls'][os.name == 'nt']) #Clears the Screen
            SUM_ALL = 0.00
            TC = 0
            env = simpy.Environment(initial_time=START)

            # print("FAST FOOD RESTAURANT SIMULATION MODEL"
            #       "\n Opened at %d:00 hours"% OPEN_TIME)
            env.process(setupenv(env, CUSTOMER_RANGE))  # Execute default setup
            env.run(until = SIM_END)

            for j in range(TEMP+1):
                TC +=1
                SUM_ALL += CALC[j]

            averageTimeService = SUM_ALL/(TEMP+1)
            servicePerSecond = 1.00/(averageTimeService*60)
            servicePerMinute = servicePerSecond*60

            #print("\n%s Model: %d counters" % (ic_info, NUM_COUNTERS))
            #print("\n%s Closed at %d:00 hours" % (ic_info, CLOSE_TIME))
            #print("\n %s Total Customers: %d" % (ic_info, (TC)))
            #print("%s Average Service time:       %.4f" % (ic_info, averageTimeService))
            #print("%s Service per minute: %f \n" % (ic_info, servicePerMinute))
            # f.write(str(averageTimeService)+'\n')
            worksheet.write(row,3, averageTimeService)
            worksheet.write(row, 0, (CLOSE_TIME-OPEN_TIME))
            worksheet.write(row, 1, TC)
            row +=1


    # f.close()

    workbook.close()
