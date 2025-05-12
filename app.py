from flask import Flask, render_template, request, send_file
from weasyprint import HTML
import os
from datetime import datetime
import base64
from pathlib import Path

app = Flask(__name__)

def encode_image_to_base64(image_path):
    with open(image_path, 'rb') as image_file:
        encoded = base64.b64encode(image_file.read()).decode('utf-8')
    ext = os.path.splitext(image_path)[1].replace('.', '')
    return f"data:image/{ext};base64,{encoded}"

@app.route('/')
def form():
    return render_template('form.html')
 
@app.route('/form2')
def form2():
    return render_template('form2.html')

@app.route('/submit1', methods=['POST'])
def submit1():
    data = request.form.to_dict()
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    base_folder = os.path.join(desktop, "pdfs")

    # Determine subfolder by age group
    age_group = data.get("age_group", "Unknown")
    if age_group == "Adult":
        folder = os.path.join(base_folder, "Adult")
    elif age_group == "Pediatric":
        folder = os.path.join(base_folder, "Pediatric")
    else:
        folder = os.path.join(base_folder, "Other")

    os.makedirs(folder, exist_ok=True)

    # Load and encode images
    logo_path = os.path.abspath("static/images/logo.png")
    bg_path = os.path.abspath("static/images/opaclogo.png")
    sign_path = os.path.abspath("static/images/sign.png")
    logo_base64 = encode_image_to_base64(logo_path)
    bg_base64 = encode_image_to_base64(bg_path)
    sign_base64 = encode_image_to_base64(sign_path)

    # Filename setup
    procedure_part = data.get('procedure', 'procedure').split('\n')[0].strip().replace(' ', '_')[:50]
    date_input = data.get('date', '')
    try:
        date_obj = datetime.strptime(date_input, '%Y-%m-%d')
        date_str = date_obj.strftime('%Y-%m-%d')
    except ValueError:
        date_str = datetime.now().strftime('%Y-%m-%d')

    filename = f"{procedure_part}_{date_str}.pdf"
    pdf_path = os.path.join(folder, filename)

    # Render and write PDF
    rendered = render_template('pdf1.html', data=data, logo_base64=logo_base64, bg_base64=bg_base64, sign_base64=sign_base64)
    pdf = HTML(string=rendered).write_pdf(stylesheets=["static/style.css"])

    with open(pdf_path, 'wb') as f:
        f.write(pdf)

    return send_file(pdf_path, as_attachment=True)


@app.route('/submit2', methods=['POST'])
def submit2():
    data = request.form.to_dict()
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    base_folder = os.path.join(desktop, "pdfs")

    age_group = data.get("age_group", "Unknown")
    if age_group == "Adult":
        folder = os.path.join(desktop,"pdfs", "Adult Ecmos")
    elif age_group == "Pediatric":
        folder = os.path.join(desktop,"pdfs", "Pediatric Ecmos")
    else:
        folder = os.path.join(desktop,"pdfs", "other")
   
    os.makedirs(folder, exist_ok=True)

    # Load and encode images
    logo_path = os.path.abspath("static/images/logo.png")
    bg_path = os.path.abspath("static/images/opaclogo.png")
    logo_base64 = encode_image_to_base64(logo_path)
    bg_base64 = encode_image_to_base64(bg_path)
    sign_path = os.path.abspath("static/images/sign.png")
    sign_base64 = encode_image_to_base64(sign_path)


    # Create PDF filename
    ecmo_part = data.get('ecmo', 'ecmo').split('\n')[0].strip().replace(' ', '_')[:50]
    Date_input = data.get('date', '')
    try:
        date_obj = datetime.strptime(Date_input, '%Y-%m-%d')
        date_str = date_obj.strftime('%Y-%m-%d')
    except ValueError:
        date_str = datetime.now().strftime('%Y-%m-%d')

    filename = f"{ecmo_part}_{date_str}.pdf"
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    pdf_path = os.path.join(folder, filename)
   
    rendered2 = render_template('pdf2.html', data=data, logo_base64=logo_base64, bg_base64=bg_base64,sign_base64=sign_base64)
    pdf2 = HTML(string=rendered2).write_pdf(stylesheets=["static/style.css"])

    with open(pdf_path, 'wb') as f:
        f.write(pdf2)

    return send_file(pdf_path, as_attachment=True)



if __name__ == '__main__':
   
    app.run(debug=True)
