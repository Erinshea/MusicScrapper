import time

class bcolors:
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def print_log(message):
    t = time.localtime()
    current_time = time.strftime("%D %H:%M:%S", t)
    print("[" + current_time + "] " + message)

def debug(message):
    print_log(message)

def error(message):
    print_log(bcolors.FAIL + message + bcolors.ENDC)

def warning(message):
    print_log(bcolors.WARNING + message + bcolors.ENDC)

def success(message): 
    print_log(bcolors.OKGREEN + message + bcolors.ENDC)

def info(message):
    print_log(bcolors.OKBLUE + message + bcolors.ENDC)
