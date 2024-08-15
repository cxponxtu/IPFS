import os
from flask import Flask, request, render_template, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import requests
import tempfile

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ipfs_files.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Defining max file size as 16MB
app.config['IPFS_API_URL'] = 'http://ipfs:5001/api/v0'

db = SQLAlchemy(app)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    cid = db.Column(db.String(100), nullable=False)

def add_to_ipfs(file_path):
    with open(file_path, 'rb') as file:
        files = {'file': file}
        response = requests.post(f'{app.config["IPFS_API_URL"]}/add', files=files)
        if response.status_code == 200:
            return response.json()['Hash']
        else:
            raise Exception(f"Failed to add file to IPFS: {response.text}")

def get_from_ipfs(cid):
    response = requests.post(f'{app.config["IPFS_API_URL"]}/cat', params={'arg': cid})
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to retrieve file from IPFS: {response.text}")

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            try:
                cid = add_to_ipfs(file_path)
                
                # Saving file into database
                new_file = File(filename=filename, cid=cid)
                db.session.add(new_file)
                db.session.commit()
                
                # Deleting the file from the server
                os.remove(file_path)  
                
                flash(f'File uploaded successfully. CID: {cid}')
            except Exception as e:
                flash(f'Error uploading to IPFS: {str(e)}')
            
            return redirect(url_for('upload_file'))
    
    files = File.query.all()
    return render_template('upload.html', files=files)

@app.route('/retrieve', methods=['GET', 'POST'])
def retrieve_file():
    if request.method == 'POST':
        cid = request.form.get('cid')
        if cid:
            try:
                file_content = get_from_ipfs(cid)
                file_record = File.query.filter_by(cid=cid).first()
                
                if file_record:
                    filename = file_record.filename
                else:
                    filename = f"file_{cid}"
                
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name
                
                return send_file(temp_path, as_attachment=True, download_name=filename)
            except Exception as e:
                flash(f'Error retrieving file from IPFS: {str(e)}')
                return redirect(url_for('retrieve_file'))
    
    return render_template('retrieve.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True,host='0.0.0.0',port=7005)