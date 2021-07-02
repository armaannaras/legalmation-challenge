from flask import Flask, request, render_template, url_for
from flask_sqlalchemy import SQLAlchemy

from flask_restful import Api
import re
import xml.etree.ElementTree as ET

from werkzeug.utils import secure_filename, redirect

app = Flask(__name__)
api = Api(app)
db = SQLAlchemy(app)


class Sample(db.Model):
    __tablename__ = 'sample'
    id = db.Column(db.Integer, primary_key=True)
    plaintiff = db.Column(db.String)
    defendant = db.Column(db.String)

    def __init__(self, plaintiff, defendant):
        self.plaintiff = plaintiff
        self.defendant = defendant

db.create_all()


def is_xml(file): #makes sure the uploaded file is an XML
    return '.' in file and \
           file.rsplit('.', 1)[1].lower() == "xml"


def parse_xml(xml): #Creates tree from xmlfor use in following 2 functions
    tree = ET.parse(xml)
    return tree.getroot()



def find_plaintiff(xml): #Finds plaintiff into by using "Plaintiff," string in xml text
    agg = []
    plain_name = ""
    for elem in parse_xml(xml).iter():
        if elem.text != None and elem.text != "":
            agg.append(elem.text)
    for i in range(len(agg)):
        if "COUNTY OF" in agg[i]: #aggregates everything after COUNTY OF and before Plaintiff in a string
            break
    for j in agg[i+1:]:
        if "Plaintiff," in j:
            break #Once we see "Plaintiff" we stop collecting
        plain_name+= j
    return re.search("(.*)[,;][^,]*$",plain_name).group(1) #Cleans up a bit of extra info. I wasn't sure what format plaintiff info can come in
                                                     #and what info is needed beyond name, so it includes everything before the last comma
                                                     #or semicolon before the word "Plaintiff"
                                                     #If the plaintiff name is on multiple lines it wouldn't work as well
                                                     #And it may be good to use the method from the defendant function


def find_defendant(xml): #Finds defendant info by locating string "Defendants."
    agg = []
    def_name = ""
    for elem in parse_xml(xml).iter():
        if elem.text != None and elem.text != "":
            agg.append(elem.text)
    for i in range(len(agg)):
        if "vs." in agg[i] or "v." in agg[i]:#aggregates everything after "vs." or "v" and before Defendant./s. in a string
            break
    for j in agg[i + 1:]:
        if "Defendants." in j:
            break
        def_name += j
    def_name = def_name[0:(def_name.rindex(","))] #Removed everything after last comma
                                                #Cleans differently from plaintiff because xml B had its defendant spread over multiple lines
                                                #So cleaning it the same way didn't work
    return re.sub(r"^\W+", "", def_name) #Removes irregular characters


@app.route("/", methods=['GET', 'POST'])
def upload():
    if request.method == "POST":
        file = request.files["file"].filename
        if not is_xml(file):
            return redirect(url_for('failure'))
        request.files["file"].save(secure_filename(file))
        plaintiff = find_plaintiff(file)
        defendant = find_defendant(file)
        sample = Sample(plaintiff=plaintiff, defendant=defendant)
        db.session.add(sample)
        db.session.commit()
    return render_template("upload.html")

@app.route('/files') #See data from previously uploaded files
def view():
    samples = Sample.query.all()
    return render_template('files.html', responses = samples)


@app.route('/failure') #Informs user that the file uploaded is not an XML
def failure():
    return render_template('failure.html')



if __name__ == '__main__':
    app.run(debug = False)