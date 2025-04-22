from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import os
import csv
import requests
import json
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load inventory data
def load_inventory_sample():
    with open('inventory.csv', mode='r') as file:
        return list(csv.DictReader(file))[:50]  # Sample 50 rows for Gemini prompt

inventory_sample = load_inventory_sample()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def query_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # Improved prompt structure
    payload = {
        "contents": [{
            "parts": [{
                "text": f"""
                You are a fashion recommendation engine. 
                Return ONLY valid JSON array without markdown or additional text.
                {prompt}
                """
            }]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()  # Will raise HTTPError for bad status
        
        # Debugging - log full response
        print("Gemini Raw Response:", response.text)
        
        data = response.json()
        
        # Handle Gemini's response structure
        if 'candidates' in data and data['candidates']:
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            print("Unexpected response structure:", data)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"API Request Failed: {str(e)}")
        return None
    except json.JSONDecodeError:
        print("Failed to decode JSON from:", response.text)
        return None

def get_recommendations(image_path, rec_type):
    with open(image_path, "rb") as img_file:
        import base64
        image_data = base64.b64encode(img_file.read()).decode("utf-8")

    # Dynamically select prompt based on rec_type
    if rec_type == "similar":
        prompt = f"""
        Analyze the uploaded fashion image (base64 encoded below) and extract key attributes:
        - gender
        - masterCategory
        - subCategory
        - articleType
        - baseColour
        - season

        Return EXACTLY this JSON:
        {{
            "gender": "string",
            "masterCategory": "string",
            "subCategory": "string",
            "articleType": "string",
            "baseColour": "string",
            "season": "string"
        }}

        Image (base64): {image_data}
        """
    elif rec_type == "accessories":
        prompt = f"""
        Analyze the uploaded fashion image (base64 encoded below) and extract key styling attributes that would help in recommending matching accessories.
        Return these:
        - gender
        - baseColour
        - season
        - usage (if visible or inferred)
        
        Return EXACTLY this JSON:
        {{
            "gender": "string",
            "baseColour": "string",
            "season": "string",
            "usage": "string"
        }}

        Image (base64): {image_data}
        """
    else:
        return []

    # Query Gemini with the selected prompt
    response_text = query_gemini(prompt)
    if not response_text:
        return []

    try:
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        extracted_attrs = json.loads(response_text)

        if isinstance(extracted_attrs, list):
            extracted_attrs = extracted_attrs[0]

    except json.JSONDecodeError as e:
        print("Gemini attribute extraction failed:", str(e))
        print("Raw response:", response_text)
        return []

    # Now match from inventory locally
    matches = []
    for item in inventory_sample:
        if rec_type == "similar":
            # Match on core features for 'similar' items
            match_score = 0
            if item['gender'].lower() == extracted_attrs['gender'].lower():
                match_score += 1
            if item['articleType'].lower() == extracted_attrs['articleType'].lower():
                match_score += 1
            if item['baseColour'].lower() == extracted_attrs['baseColour'].lower():
                match_score += 1
            if item['season'].lower() == extracted_attrs['season'].lower():
                match_score += 1
            if match_score >= 2:  # threshold to consider it a match
                matches.append(item)

        elif rec_type == "accessories":
            # Match accessories based on articleType (belts, shoes, sunglasses, etc.)
            # Allow any item that is an accessory type (like 'belt', 'shoes', 'sunglasses')
            accessory_types = ['belt', 'shoe', 'sunglass', 'watch', 'scarf', 'jewelry', 'bag', 'hat']
            if any(accessory in item['articleType'].lower() for accessory in accessory_types):
                match_score = 0
                if item['gender'].lower() == extracted_attrs['gender'].lower():
                    match_score += 1
                if item['baseColour'].lower() == extracted_attrs['baseColour'].lower():
                    match_score += 1
                if item['season'].lower() == extracted_attrs['season'].lower():
                    match_score += 1
                if match_score >= 1:  # threshold to consider it a match
                    matches.append(item)

    # Shuffle and return 5–6 results
    import random
    random.shuffle(matches)
    selected = matches[:6]
    
    print([item["file_path"] for item in selected])
    # Return only the file_path for the selected items
    return [f"/static/{item['file_path']}" for item in selected]


# Routes
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    age = int(request.form['age'])
    address = request.form['address']
    pincode = request.form['pincode']
    
    if age < 30:
        return redirect(url_for('young', name=name))
    else:
        return redirect(url_for('elder', name=name))

@app.route('/young')
def young():
    name = request.args.get('name', 'Guest')
    return render_template('young.html', name=name)

@app.route('/elder')
def elder():
    name = request.args.get('name', 'Guest')
    return render_template('elder.html', name=name)

@app.route('/recommend', methods=['POST'])
def recommend():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    
    similar_items = get_recommendations(save_path, "similar")
    accessories = get_recommendations(save_path, "accessories")
    
    return jsonify({
        'uploaded_image': f"/static/uploads/{filename}",
        'similar': similar_items,
        'accessories': accessories
    })

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/cart")
def view_cart():
    return render_template("cart.html")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)