from torpy import TorClient

hostname = "ifconfig.me"

print("started")
with TorClient() as tor:
  print("created the client")
  with tor.create_circuit(3) as circuit:
    print("created the circuit")
    with circuit.create_stream((hostname,80)) as stream:
      print("stream created")
      stream.send(b'GET /HTTP/1.0\r\nHost: %s\r\n\r\n' % hostname.encode())
      print("message sent")
      recv = stream.recv(1024)
      print("message received")
      print(recv)