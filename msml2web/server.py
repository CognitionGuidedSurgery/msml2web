# region gplv3preamble
# The Medical Simulation Markup Language (MSML) - Simplifying the biomechanical modeling workflow
#
# MSML has been developed in the framework of 'SFB TRR 125 Cognition-Guided Surgery'
#
# If you use this software in academic work, please cite the paper:
# S. Suwelack, M. Stoll, S. Schalck, N.Schoch, R. Dillmann, R. Bendl, V. Heuveline and S. Speidel,
# The Medical Simulation Markup Language (MSML) - Simplifying the biomechanical modeling workflow,
# Medicine Meets Virtual Reality (MMVR) 2014
#
# Copyright (C) 2013-2014 see Authors.txt
#
# If you have any questions please feel free to contact us at suwelack@kit.edu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# endregion

import json
import uuid

import markdown


__author__ = 'Alexander Weigl'
__date__ = "2014-07-19"

from flask import Flask, request, render_template, Response, send_from_directory, url_for, redirect
from flask.ext.restful import Api

import sys

sys.path.append("../msml/src")

from msml.frontend import App as MSMLApp
import msml.sorts
import msml.model

msmlapp = MSMLApp()
alphabet = msmlapp.alphabet

OUTPUT_DIRECTORIES = {
    "TEST": "/tmp/test"
}


def error(msg, no=500):
    """returns a formatted error object for json

    :param msg: error message
    :param no: error number (unique identifier)
    :return: dict
    :rtype: dict
    """
    return make_json_response({'message': msg, 'number': no})


def slots(slots):
    """

    :param slots:
    :return:
    """
    return [(s.name, s.physical_type, s.logical_type)
            for s in slots.values()]


import tempfile
from path import Path


def prepare_run(operator):
    root = Path(tempfile.mkdtemp("msml_operator"))

    def get_files(inputs):
        input_files = {}
        for n in inputs:
            fil = request.files[n]
            input_files[n] = str(root / fil.filename)
            fil.save(input_files[n])
        return input_files

    def get_parameters(parameters):
        arguments = {}
        for slot in parameters.values():
            value = request.values.get(slot.name, slot.default)
            # maybe to strong requirement:
            # if not value:
            #     for k,i in request.values.iteritems():
            #         print k,i
            #     raise KeyError("operator slot %s is not given" % slot.name)

            if slot.target:  # prefix output parameter to working directory, prevent breakout
                value = str(root / value)

            cnv = msml.sorts.conversion(type(value), slot.sort)(value)
            arguments[slot.name] = cnv
        return arguments

    a = get_files(operator.input)
    a.update(get_parameters(operator.parameters))

    token = str(uuid.uuid4())
    OUTPUT_DIRECTORIES[token] = root

    return token, a


def request_wants_json():
    """Returns True iff. the current requests prefers json over html"""
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
           request.accept_mimetypes[best] > \
           request.accept_mimetypes['text/html']


def make_json_response(obj, status=None, ):
    return Response(json.dumps(obj), status=status, mimetype="application/json")


def is_file_input(slot):
    # print slot.sort.physical, isinstance(slot.sort.physical, msml.sorts.InFile)
    return issubclass(slot.sort.physical, msml.sorts.InFile)


def firstline(string):
    """returns the first line of contents in string

    :param string:
    :return:
    """
    string = string.strip()
    pos = min(string.find("\n"), string.find(".")+1, 64)

    if pos:
        return string[:pos]
    else:
        return string

def shortmd(md):
    s = markdown.markdown(md).strip()
    if s.startswith("<p>") and s.endswith("</p>"):
        return s[3:-4]
    else:
        return s

def setup():
    app = Flask(__name__)
    api = Api(app)

    app.jinja_env.filters["markdown"] = shortmd
    app.jinja_env.filters["firstline"] = firstline
    app.jinja_env.globals['is_file_input'] = is_file_input
    app.jinja_env.globals['_bool'] = msml.sorts._bool

    @app.route("/")
    def home():
        return render_template("index.html", title="MSML as a Service")

    @app.route("/operators/")
    def list_operators():
        if request_wants_json():
            operator_names = [(name) for name in alphabet.operators.keys()]
            return make_json_response(operator_names)
        else:
            return render_template("operators.html", operators=alphabet.operators)

    @app.route("/operators/<string:name>")
    def opget(name):
        try:
            operator = alphabet.operators[name]
            if request_wants_json():
                return make_json_response({
                    'name': operator.name,
                    'input': slots(operator.input),
                    'output': slots(operator.output),
                    'parameter': slots(operator.parameters),
                    'type': operator.sort.physical.__name__,
                    'meta': operator.meta
                })
            else:
                return render_template("operatorform.html", operator=operator)
        except KeyError as e:
            return error("Operator not found: %s" % e)


    @app.route("/operators/<string:name>", methods=["POST"])
    def opsubmit(name):
        print name
        try:
            operator = alphabet.operators[name]
            operator.bind_function()
            try:
                token, arguments = prepare_run(operator)
                result = operator(**arguments)
                for out in result:
                    if is_file_input(operator.output[out]):
                        path = Path(result[out])
                        result[out] = request.url_root[:-1] + url_for("get",token = token,
                                                            filename = path.name)

                if request_wants_json():
                    return make_json_response(result)
                else:
                    return str(result)
                    #return redirect(url_for("list", token = token))
            except KeyError as e:
                return error(e.message)
        except KeyError as e:
            return error("Operator not found: %s" % e)

    @app.route("/get/<string:token>")
    def list(token):
        try:
            pth = Path(OUTPUT_DIRECTORIES[token])

            if not pth.exists():
                raise KeyError()

            files = pth.listdir()
            if request_wants_json():
                result = [
                    url_for("get", token=token, filename = f.name)
                    for f in files
                ]
                return make_json_response(result)
            else:

                return render_template("dir.html", token=token, files=files)

        except KeyError:
            print OUTPUT_DIRECTORIES
            return "Token invalid"


    @app.route("/get/<string:token>/<path:filename>")
    def get(token, filename):
        try:
            pth = Path(OUTPUT_DIRECTORIES[token])
            filename = pth / filename

            if not pth.exists():
                return 404, "File not exists"

            return send_from_directory(filename.dirname(), filename.name)

        except KeyError:
            return "Token invalid"

    # api.add_resource(OperatorResource, '/operators/<string:operator_name>', endpoint='or')
    return app