#!/usr/bin/env python3
"""
Very simple HTTP server in python for logging requests
Usage::
    ./server.py [<port>]
"""


# test it with:
#
# > curl -X POST -d "user=Hello&pass=World" http://localhost:8080
#
# or
#
# > curl -d '{"user":"Hello", "password":"World"}' -H "Content-Type: application/json" -X POST http://localhost:8080/data


from http.server import BaseHTTPRequestHandler, HTTPServer
import logging


class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self):
        logging.info(f"GET request,\nPath: {self.path}\nHeaders:\n{self.headers}\n")
        self._set_response()
        self.wfile.write(f"GET request for {self.path}".encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])  # <- Gets the size of data
        post_data = self.rfile.read(content_length)  # <- Gets the data itself
        logging.info(
            f"POST request,\nPath: {self.path}\nHeaders:\n{self.headers}\n\nBody:\n{post_data.decode('utf-8')}\n"
        )

        self._set_response()
        self.wfile.write(f"POST request for {self.path}".encode("utf-8"))


def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    logging.info("Starting httpd...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping httpd...\n")


if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
