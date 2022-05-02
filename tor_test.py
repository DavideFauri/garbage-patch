from torpy import TorClient
from torpy.http import requests as tor_requests
from torpy.http.adapter import TorHttpAdapter

hostname = "ifconfig.me"

print("v1: started")

with TorClient() as tor:

  print("v1: defined client")
  
  with tor.create_circuit(3) as circuit:
    
    print("v1: created circuit")
    
    with circuit.create_stream((hostname,80)) as stream:

      print("v1: created stream")

      stream.send(b'GET / HTTP/1.0\r\nHost: %s\r\n\r\n' % hostname.encode())
      ret = recv_all(stream).decode()
      print(ret)

# ---------------
print()
# ---------------

print('v2: started')

with TorClient() as tor:

  print("v2: defined client")

  with tor.get_guard() as guard:

    print("v2: created guard")

    adapter = TorHttpAdapter(guard=guard, hops_count=3)

    print("v2: created adapter")

    with tor_requests.Session() as sess:

      print("v2: created session")

      sess.headers.update({'User-Agent': 'Mozilla/5.0'})
      sess.mount(prefix = 'http://', adapter=adapter)
      sess.mount(prefix = 'https://', adapter=adapter)

      print("v2: configured session")

      response = sess.get(url=hostname)
      print(response.text)

