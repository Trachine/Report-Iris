from colorama import Fore, Style

def log_warning(msg):
    print(f"{Fore.RED}[WARNING]{Style.RESET_ALL} {msg}")

def log_info(msg):
    print(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} {msg}")

def log_done(msg):
    print(f"{Fore.GREEN}[DONE]{Style.RESET_ALL} {msg}")
