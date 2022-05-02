# import grequests
import requests
import random
import argparse
from pathlib import Path
from time import sleep
import genexp


## test with: ##

# python ./garbage-patch.py -t http://localhost:8080 -p user -x "usr\\W\\d{3}\\!?" -p pass -w ./wordlist/ITA/bruteforce.txt -v -p tel -m IT -S 2

##

##################
# TODO
# send requests via Tor through multiple IPs
# https://stackoverflow.com/questions/30286293/make-requests-using-python-over-tor
##################
##################
# TODO
# make list of realistic User-Agent, randomize those too
##################


# -----------------------------------------------------------------------------

class Poisoner():
    def __init__(self) -> None:
        pass
    def generate(self) -> str:
        return ""

# -------------------------------------

class WordListPoisoner(Poisoner):

    def __init__(self, filepath:str):        
        assert Path(filepath).exists(), f"The file {filepath} does not exist!"

        wordset = set[str]()
        with open(Path(filepath)) as wordlist:
            for w in wordlist:
                wordset.add(w.strip())
        self.words = list(wordset)

        super().__init__()
    
    def generate(self):
        return random.choice(self.words)

# -------------------------------------

class GenexPoisoner(Poisoner):

    def __init__(self, genex_str:str):
        self.genex = genexp.parse(genex_str)
        super().__init__()
    
    def generate(self):
        return self.genex.generate()

# -------------------------------------

class TelephonePoisoner(GenexPoisoner):

    # fmt: off
    countries = {
        "IT": {# https://it.wikipedia.org/wiki/Prefissi_telefonici_dei_cellulari_italiani
            "prefix": [320,324,327,328,329,330,331,333,334,335,336,337,338,339,340,342,344,345,346,347,348,349,350,351,352,360,366,368,371,373,375,377,380,388,389,391,392,393],
            "format": "\\d{7}"
        }
    }
    # fmt: on

    def __init__(self, countrycode:str):
        self.prefixes = "(" + "|".join(str(prefix) for prefix in TelephonePoisoner.countries[countrycode]["prefix"]) + ")"
        self.numbers = TelephonePoisoner.countries[countrycode]["format"]

        super().__init__(self.prefixes + self.numbers)
    
    def generate(self):
        return super().generate()    


# -----------------------------------------------------------------------------



# -----------------------------------------------------------------------------

def parse_arguments():

    parser = argparse.ArgumentParser()
    # fmt: off
    parser.add_argument("-t", "--target", metavar=("ADDR"), action="append", required=True,
                        help="web address(es) of the POST target(s)",
    )
    parser.add_argument("-p", "--param-name", action="append", required=True, dest="params",
                        help="name of each parameter to send via POST",
    )
    parser.add_argument("-w", "--wordlist", metavar=("FILE"), action=CreatePoisoner, dest="sources",
                        help="wordlist file from which a line is sampled",
    )
    parser.add_argument("-x", "--regex", metavar=("REGEX"), action=CreatePoisoner, dest="sources",
                        help="generative regex-like pattern (ex. 'pwd\\W\\d{3}\\!' -> 'pwdA123@')",
    )
    parser.add_argument("-m", "--mobile", metavar=("CTRYCODE"), action=CreatePoisoner, dest="sources", choices=TelephonePoisoner.countries.keys(),
                        help="country code used to generate realistic mobile numbers",
    )
    parser.add_argument("-c", "--count", type=int, default=0,
                        help="number of POST attempts (0 = no limit)",
    )
    parser.add_argument("-s", "--sleep-min", type=float, default=0.1,
                        help="min number of seconds to wait between POSTs",
    )
    parser.add_argument("-S", "--sleep-max", type=float, default=10,
                        help="max number of seconds to wait between POSTs",
    )
    parser.add_argument("-v", "--verbose", action="store_true"
    )
    # fmt: on

# FIXME

    # arg_str = "-t http://localhost:8080 -p user -x usr\\W\\d{3}\\!? -p pass -w ./wordlistITA/bruteforce.txt -v -p tel -m IT -S 2"
    # args = parser.parse_args(arg_str.split())

# FIXME

    args = parser.parse_args()

    error_string = (
        "Each parameter requires a single data source (file or regex)!\n"
        + "Params defined:\n"
        + "\n".join(args.params)
    )
    assert args.sources != None, error_string
    assert len(args.params) == len(args.sources), error_string

    print(args)


    return args

# -------------------------------------

class CreatePoisoner(argparse.Action):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def __call__(self,_,namespace,values: str,option_string: str):
        arg_list = getattr(namespace, self.dest) or []
        match option_string:
            case "-w" | "--wordlist":
                poisoner=WordListPoisoner(values)
            case "-x" | "--regex":
                poisoner=GenexPoisoner(values)
            case "-m" | "--mobile":
                poisoner=TelephonePoisoner(values)
            case _:
                poisoner=None
        arg_list.append(poisoner)
        setattr(namespace, self.dest, arg_list)


# -----------------------------------------------------------------------------


def make_data(args):
    data = {}
    for (param,source) in zip(args.params, args.sources):
        data[param] = source.generate()

    if args.verbose:
        print("Generating random data to POST: ", end="")
        print(data)
    
    return data


# -----------------------------------------------------------------------------


def wait(args):
    sleep_duration = (
    random.randint(args.sleep_min * 1000, args.sleep_max * 1000) / 1000.0
    )

    if args.verbose:
        print(f"Sleeping for {sleep_duration} seconds...")
    
    sleep(sleep_duration)

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        args = parse_arguments()
    
        runs = 0
        while args.count == 0 or runs < args.count :
            runs += 1

            for address in args.target:
                data = make_data(args)
                
                if args.verbose:
                    print(f"Sending data to {address}...")
                
                r = requests.post(url=address, data=data)

                if r:
                    if args.verbose:
                        print("Data sent successfully.")

                wait(args)

    except Exception as e:
        print(e)
