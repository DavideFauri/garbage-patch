from pathlib import Path
import os
import requests
import gzip
import json
import random


# check for existence of (recent?) gzip file

user_agent_repo = Path("./user-agents.json.gz")

if not user_agent_repo.exists():

  print("user agent archive not found, downloading...")

  r = requests.get("https://github.com/intoli/user-agents/raw/master/src/user-agents.json.gz")
  with open(user_agent_repo, "wb") as compressed:
    compressed.write(r.content)


with gzip.open("./user-agents.json.gz", 'rb') as compressed:
  
  user_agent_data = json.load(compressed)

  user_agent_strings = [entry["userAgent"] for entry in user_agent_data]
  user_agent_weights = [entry["weight"] for entry in user_agent_data]

def generate():
  return random.choices(population=user_agent_strings, weights=user_agent_weights)[0]

