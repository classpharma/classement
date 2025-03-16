from flask import Flask, render_template, request
import os
import re
from PyPDF2 import PdfReader

app = Flask(__name__)

# Folder to store uploaded files temporarily
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to extract data from PDF
def extract_data_from_pdf(file_path, extract_ids_only=False):
    reader = PdfReader(file_path)
    results = []
    for page in reader.pages:
        text = page.extract_text()
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

# Function to compare student results
def compare_notes_with_ue14_only(colle_path, ue14_path, target_id):
    if not os.path.exists(colle_path) or not colle_path.endswith(".pdf"):
        raise ValueError(f"Fichier non valide : {colle_path}")
    if not os.path.exists(ue14_path) or not ue14_path.endswith(".pdf"):
        raise ValueError(f"Fichier non valide : {ue14_path}")
    
    ue14_ids = extract_data_from_pdf(ue14_path, extract_ids_only=True)
    students = extract_data_from_pdf(colle_path)
    
    target_student = next((s for s in students if s["id"] == target_id), None)
    if not target_student:
        raise ValueError(f"Étudiant avec ID {target_id} introuvable.")
    
    general_higher = [s for s in students if s["note"] > target_student["note"]]
    classement_general = len(general_higher) + 1
    total_students = len(students)
    
    pharma_students = [s for s in students if s["id"] in ue14_ids]
    pharma_higher = [s for s in pharma_students if s["note"] > target_student["note"]]
    classement_pharma = len(pharma_higher) + 1
    total_pharma = len(pharma_students)
    
    return {
        "classement_general": f"{classement_general}/{total_students}",
        "classement_pharma": f"{classement_pharma}/{total_pharma}",
        "pharma_mieux": len(pharma_higher),
        "pharma_pire": total_pharma - len(pharma_higher)
    }

# Route to display form and handle file uploads
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    
    if request.method == "POST":
        try:
            colle_file = request.files["colle"]
            ue14_file = request.files["ue14"]
            target_id = request.form["target_id"].strip()
            
            colle_path = os.path.join(UPLOAD_FOLDER, colle_file.filename)
            ue14_path = os.path.join(UPLOAD_FOLDER, ue14_file.filename)
            
            colle_file.save(colle_path)
            ue14_file.save(ue14_path)
            
            result = compare_notes_with_ue14_only(colle_path, ue14_path, target_id)
        except Exception as e:
            error = str(e)
    
    return render_template("index.html", result=result, error=error)

if __name__ == "__main__":
    app.run(debug=True)
