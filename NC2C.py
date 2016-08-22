#!/usr/bin/python3

import os
import sys
import random
import datetime
import simpy
import xlsxwriter

# ==============================================================================
"""
Setting variables
"""
global STATE, TEMP #, SUM_ALL
STATE = 0
TEMP = 0
CALC = [0] * 500  # Input capacity
TC= 0

# Simulation time in minutes
HOUR_OPEN = 7  # Morning
HOUR_CLOSE = 21  # Night
START = HOUR_OPEN * 60
SIM_TIME = HOUR_CLOSE * 60

SIM_FACTOR = 1 / 60  # Simulation realtime factor
PEAK_START = 11
PEAK_END = 13
PEAK_TIME = 60 * (PEAK_END - PEAK_START)  # Range of peak hours

NUM_COUNTERS = 2  # Number of counters in the drive-thru
# Minutes it takes in each counters
TIME_COUNTER_A = 3
TIME_COUNTER_B = 2
TIME_COUNTER_C = 1

# Create a customer every [min, max] minutes
CUSTOMER_RANGE_NORM = [5, 10]  # in normal hours
CUSTOMER_RANGE_PEAK = [1, 5]  # in peak hours
CUSTOMER_RANGE = CUSTOMER_RANGE_NORM

# ==============================================================================
"""
Defining Queue properties
"""


def toc(raw):
    clock = ('%02d:%02d' % (raw / 60, raw % 60))
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

ic_in = cy("[waiting]")
ic_go = cy("[checkout]")
ic_lv = cy("[left]")
ic_info = cb("[information]")
ic_ask = cm("[ask]")
ic_mon = cg("[paid]")
ic_stop = cr("[hold]")
ic_dang = cr("[closed]")

# =============================================================================
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


# ==============================================================================
"""
First+Second counter class
"""


class counterFirstSecond(object):
    def __init__(self, env):
        self.env = env
        self.employee = simpy.Resource(env, 1)

    def serve(self, cust):
        yield self.env.timeout(random.randint(TIME_COUNTER_A - 1, TIME_COUNTER_A + 1))
        # print("%s (%s) %s ordered the menu" % (ic_ask, cgray(toc(env.now)), cust))

        yield self.env.timeout(random.randint(TIME_COUNTER_B - 1, TIME_COUNTER_B + 1))
        # print("%s (%s) %s paid the order" % (ic_mon, toc(env.now), cust))


# ==============================================================================
"""
Third counter class
"""


class counterThird(object):
    def __init__(self, env):
        self.env = env
        self.employee = simpy.Resource(env, 1)

    def serve(self, cust):
        yield self.env.timeout(random.randint(TIME_COUNTER_C - 1, TIME_COUNTER_C + 1))
        #  print("%s (%s) %s took the order" % (ic_stop, toc(env.now), cust))


# ==============================================================================

"""
(Type 2) Define customer behavior at first counter
"""


def customer2A(env, name, wl, ce12, ce3):
    with wl.lane.request() as request:

        if (env.now >= SIM_TIME):
            #       print("%s Not enough time! %s cancelled" % (ic_dang, name))
            env.exit()

        yield request
        yield env.process(wl.serve(name))
        # print("%s (%s) %s is in waiting lane" % (ic_in, toc(env.now), name))

    # Start the actual drive-thru process
    # print("%s (%s) %s goes into drive-thru counter" % (ic_go, toc(env.now), name))

    with ce12.employee.request() as request:

        if (env.now + TIME_COUNTER_A + TIME_COUNTER_B >= SIM_TIME):
            #   print("%s Not enough time! Assumed %s is quickly finished" % (ic_dang, name))
            yield env.timeout(0.5)
            env.exit()

        yield request

        CALC[int(name[5:])] = env.now
        yield env.process(ce12.serve(name))
        # print("%s (%s) %s choose the order" % (ic_ask, toc(env.now), name))

        yield env.process(ce12.serve(name))
        # print("%s (%s) %s is paying and will take the order" % (ic_mon, toc(env.now), name))
        env.process(customer2B(env, name, ce12, ce3))


"""
(Type 2) Define customer behavior at second counter
"""


def customer2B(env, name, ce12, ce3):
    with ce3.employee.request() as request:
        if (env.now + TIME_COUNTER_C >= SIM_TIME):
            #   print("%s Not enough time! Assumed %s is quickly finished" % (ic_dang, name))
            yield env.timeout(0.5)
            env.exit()

        yield request

        yield env.process(ce3.serve(name))
        # print("%s (%s) %s leaves" % (ic_lv, toc(env.now), name))

        global TEMP
        TEMP = int(name[5:])
        CALC[int(name[5:])] = env.now - CALC[int(name[5:])]


# ==============================================================================
"""
Default Environment with 2 counters
"""


def defaultsetup(env, cr):
    # Create all counters
    wl = waitingLane(env)
    ce12 = counterFirstSecond(env)
    ce3 = counterThird(env)
    i = 0

    # Create more customers while the simulation is running
    while True:
        yield env.timeout(random.randint(*cr))
        i += 1
        env.process(customer2A(env, "Cust %d" % i, wl, ce12, ce3))


# ==============================================================================
"""
main program
"""
if __name__ == "__main__":

    workbook = xlsxwriter.Workbook('NC2C.xlsx')
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, "Total Hours:")
    worksheet.write(0, 1, "Total Coustomers:")
    worksheet.write(0, 3, "Average Service time:")
    row = 1
    for i in range(0, 499):

        os.system(['clear', 'cls'][os.name == 'nt'])  # Clears the Screen
        SUM_ALL = 0.00
        TC = 0
        env = simpy.Environment(initial_time=START)
        # print(""" Restaurant Queuing Drive-Thru Model Simulation (N customers - 2 counters)""")
        env.process(defaultsetup(env, CUSTOMER_RANGE))  # Execute default setup
        env.run(until=SIM_TIME)

        for j in range(TEMP + 1):
            TC += 1
            SUM_ALL += CALC[j]

        averageTimeService = SUM_ALL / (TEMP + 1)
        servicePerSecond = 1.00 / (averageTimeService * 60)
        servicePerMinute = servicePerSecond * 60

        # print("%s Model: %d counters" % (ic_info, nc))
        # print("%s Total Customers:       %d" % (ic_info, TC))
        # print("%s Average Service time:       %.4f" % (ic_info, averageTimeService))
        # print("%s Service per minute: %f" % (ic_info, servicePerMinute))
        worksheet.write(row, 3, averageTimeService)
        worksheet.write(row, 0, (HOUR_CLOSE - HOUR_OPEN))
        worksheet.write(row, 1, TC)
        row += 1

# f.close()

workbook.close()

