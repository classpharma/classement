from flask import Flask, request, jsonify, send_from_directory
from PyPDF2 import PdfReader
import os
import re
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

PHARMA_IDS_PATH = 'static/ue14_only.pdf'

# Valider le fichier
def validate_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")
    if not file_path.endswith(".pdf"):
        raise ValueError(f"Fichier non valide (attendu PDF) : {file_path}")

# Extraire les données du PDF
def extract_data_from_pdf(file_path, extract_ids_only=False):
    reader = PdfReader(file_path)
    results = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            lines = text.splitlines()
            for line in lines:
                if extract_ids_only:
                    ids = re.findall(r"\b\d{8,9}\b", line)
                    results.extend(ids)
                else:
                    match = re.match(r"(\d{8,9})\s+([\d,]+)\s+(\d+)", line)
                    if match:
                        student_id = match.group(1)
                        note = float(match.group(2).replace(',', '.'))
                        classement = int(match.group(3))
                        results.append({"id": student_id, "note": note, "classement": classement})
    return set(results) if extract_ids_only else results

# Comparer les notes
def compare_notes_with_ue14_only(colle_results_path, ue14_ids_set, target_id):
    students_data = extract_data_from_pdf(colle_results_path)
    target_student = next((s for s in students_data if s['id'] == target_id), None)
    if not target_student:
        return {"error": f"Étudiant avec ID {target_id} introuvable dans les résultats."}

    general_higher = [s for s in students_data if s['note'] > target_student['note']]
    classement_general = len(general_higher) + 1
    total_students = len(students_data)

    pharma_students = [s for s in students_data if s['id'] in ue14_ids_set]
    pharma_higher = [s for s in pharma_students if s['note'] > target_student['note']]
    classement_pharma = len(pharma_higher) + 1
    total_pharma = len(pharma_students)

    return {
        "classement_general": f"{classement_general}/{total_students}",
        "classement_pharma": f"{classement_pharma}/{total_pharma}"
    }

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/compare', methods=['POST'])
def compare():
    if 'file' not in request.files or 'student_id' not in request.form:
        return jsonify({"error": "Fichier ou ID manquant."})

    file = request.files['file']
    student_id = request.form['student_id']

    if file.filename == '':
        return jsonify({"error": "Aucun fichier sélectionné."})

    filename = f"{uuid.uuid4()}.pdf"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        pharma_ids = extract_data_from_pdf(PHARMA_IDS_PATH, extract_ids_only=True)
        result = compare_notes_with_ue14_only(filepath, pharma_ids, student_id)
    except Exception as e:
        result = {"error": str(e)}

    # Nettoyage automatique du fichier uploadé
    if os.path.exists(filepath):
        os.remove(filepath)

    return jsonify(result)

@app.route('/')
def index():
    return send_from_directory('.', 'templates/index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
