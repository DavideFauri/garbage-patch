import requests
import threading
import random
import argparse
from pathlib import Path
from time import sleep
import genexp


## to test garbage generation:

# Terminal 1:
# python ./http-listener.py

# Terminal 2:
# python ./garbage-patch.py -u http://localhost:8080 -p user -x "usr\\W\\d{3}\\!?" -p pass -w ./wordlist/ITA/bruteforce.txt -p tel -m IT -S 2 -v


## to test multitarget/multithreading:

# Terminal 1:
# python ./http-listener.py 8080

# Terminal 2:
# python ./http-listener.py 8081

# Terminal 3:
# python ./garbage-patch.py -u http://localhost:8080 -u http://localhost:8081 -p test_param -x "test_\d\d" -t 2 -s 1 -S 2 -v


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
        self.optional_space = " ?"
        self.numbers = TelephonePoisoner.countries[countrycode]["format"]

        super().__init__(self.prefixes + self.optional_space + self.numbers)

    def generate(self):
        return super().generate()

# -----------------------------------------------------------------------------

def parse_arguments():

    parser = argparse.ArgumentParser()
    # fmt: off
    parser.add_argument("-u", "--url", metavar=("URL"), action="append", required=True,
                        help="URL address of each POST target",
    )
    parser.add_argument("-p", "--param", action="append", required=True, dest="params",
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
                        help="total count of POST attempts (0 = no limit)",
    )
    parser.add_argument("-t", "--threads", type=int, default=1,
                        help="number of threads to use for each target URL"
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

    args = parser.parse_args()

    ## validation

    error_string = (
        "Each parameter requires a single data source (file or regex)!\n"
        + "Params defined:\n"
        + "\n".join(args.params)
    )
    assert args.sources != None, error_string
    assert len(args.params) == len(args.sources), error_string

    assert args.count >=0, "The value for --count must be 0 or higher!"
    assert args.threads >=1, "The value for --threads must be 1 or higher!"

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

def countdown(count):
    if count == 0:
        while True:
            yield True
    else:
        for _ in range(count):
            yield True

# -----------------------------------------------------------------------------

def do_request(url, args):

    for _ in countdown(args.count):
        data = make_data(args)

        if args.verbose:
            print(f"Sending data to {url}...")

        response = requests.post(url=url, data=data)

        if not response.ok and args.verbose:
            print(f"ERR {response.status_code}: {response.reason}")

        wait(args)

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        args = parse_arguments()

        request_function = do_request
        request_threads = []

        for url in args.url:

            def this_request():
                return request_function(url, args)

            for _ in range(args.threads):
                t = threading.Thread(target=this_request)
                t.daemon=True
                request_threads.append(t)

            for t in request_threads:
                t.start()

            for t in request_threads:
                t.join()


    except Exception as e:
        print(e)
