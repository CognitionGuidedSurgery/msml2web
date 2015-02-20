import msml2web

app = msml2web.setup()

from flask import Flask, url_for
from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware
 
#app.config["APPLICATION_ROOT"] = "/abc/123"


def simple(env, resp):
    resp(b'200 OK', [(b'Content-Type', b'text/plain')])
    return [b"Hello WSGI World"]
 
 
parent_app = DispatcherMiddleware(simple, {"/msml": app})
 
if __name__ == "__main__":
    run_simple('0.0.0.0', 5000, parent_app)

