FROM wadoon/msml

MAINTAINER Alexander Weigl <Alexander.Weigl@student.kit.edu>

EXPOSE 5000

RUN pip install Flask gunicorn

ENV PYTHONPATH /app

# FOR WSGI
#ENV SCRIPT_NAME /msml

ADD . /app

WORKDIR /app

RUN sudo pip install -r requirements.txt

ADD gunicornconfig.py /etc/gunicornconfig.py

ENTRYPOINT gunicorn -c /etc/gunicornconfig.py testserver:app