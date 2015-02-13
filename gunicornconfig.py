bind = "0.0.0.0:5000"
workers = 3

# from wadoon/msml container
pythonpath="/msml/src/"

#max_requests = 1024
#preload_app = True
#pidfile = "/tmp/gunicorn.pid"
accesslog = "-" # stderr
errorlog = "-" # stderr
