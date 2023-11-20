from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from pymongo import MongoClient
from mindee import Client, product
import os
from datetime import datetime
from bson import ObjectId
from flask import send_file
import base64

app = Flask(__name__)

# MongoDB configuration
# client = MongoClient('mongodb://localhost:27017/')
client = MongoClient('add_str_addres')
db = client['pdf_data_new']

# Mindee API configuration
mindee_client = Client(api_key="Add_API_Key")

# Set up the uploads folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Custom Jinja filter to extract information from the output_text
@app.template_filter('extract')
def extract(text, key):
    start = text.find(f'{key}:') + len(key) + 1
    end = text.find('\n', start)
    return text[start:end].strip()

@app.route('/')
def home():
    # Fetch data from MongoDB
    collection = db['pdf_data']
    documents = collection.find()
    return render_template('home.html',documents=documents)

@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            # Save the uploaded file locally
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            # Load the file and parse it using Mindee API
            input_doc = mindee_client.source_from_path(file_path)
            result = mindee_client.parse(product.InvoiceV4, input_doc)
            # Convert the Document object to a string for storage
            output_text = str(result.document)
            # Store the result in MongoDB
            collection = db['pdf_data']
            uploaded_from = "Web"
            upload_datetime = datetime.now() 
            document = {
                'input_file': file_path,
                'output_text': output_text,
                "uploaded_from": uploaded_from,
                'upload_datetime': upload_datetime
            }
            collection.insert_one(document)
            return redirect(url_for('home')) 
    return render_template("upload.html")
            # return jsonify({'message': f'File {file.filename} successfully uploaded and processed. Result stored in MongoDB.'})

@app.route('/view_data/<file_id>')
def view_data(file_id):
    # Retrieve data from MongoDB
    collection = db['pdf_data']
    document = collection.find_one({'_id': ObjectId(file_id)})
    # print(document)
    if document:
        return render_template('newviewdata.html', document=document)
    else:
        return jsonify({'error': 'File not found'})

@app.route('/view_invoice/<file_id>')
def view_pdf(file_id):
    # Retrieve file path from MongoDB
    collection = db['pdf_data']
    document = collection.find_one({'_id': ObjectId(file_id)})

    if document:
        file_path = document['input_file']
        
        # Read the PDF file content
        with open(file_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
        
        # Encode the PDF content in base64
        encoded_pdf = base64.b64encode(pdf_content).decode('utf-8')
        
        return render_template('viewinvoice.html', encoded_pdf=encoded_pdf)
    else:
        return jsonify({'error': 'File not found'})


@app.route('/delete_content/<file_id>')
def delete_content(file_id):
    # Retrieve file path from MongoDB
    collection = db['pdf_data']
    document = collection.find_one({'_id': ObjectId(file_id)})
    documents = collection.find()
    if document:
        # Delete file locally
        file_path = document['input_file']
        os.remove(file_path)
        # Delete document from MongoDB
        collection.delete_one({'_id': ObjectId(file_id)})
        return render_template('home.html',documents=documents)
        # return jsonify({'message': 'Content deleted successfully'})
    else:
        return jsonify({'error': 'File not found'})

if __name__ == '__main__':
    app.run(debug=True)
