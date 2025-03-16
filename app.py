import os
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
import re

app = Flask(__name__)

# Assurer que le fichier ue14_only.pdf est dans le dossier static
UE14_FILE_PATH = os.path.join(app.root_path, 'static', 'ue14_only.pdf')

# Fonction pour extraire les données des fichiers PDF
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

# Comparer les notes avec le fichier UE14
def compare_notes_with_ue14_only(colle_results_path, target_id):
    ue14_only_ids = extract_data_from_pdf(UE14_FILE_PATH, extract_ids_only=True)
    students_data = extract_data_from_pdf(colle_results_path)
    
    target_student = next((student for student in students_data if student["id"] == target_id), None)
    if not target_student:
        return {"error": f"Étudiant avec ID {target_id} introuvable dans les résultats de la colle."}
    
    # Calcul du classement général (tous les étudiants)
    general_higher = [student for student in students_data if student["note"] > target_student["note"]]
    classement_general = len(general_higher) + 1
    total_students = len(students_data)

    # Filtrer les étudiants pharma (ceux présents dans le fichier ue14_only)
    pharma_students = [student for student in students_data if student["id"] in ue14_only_ids]
    pharma_higher = [student for student in pharma_students if student["note"] > target_student["note"]]
    classement_pharma = len(pharma_higher) + 1
    total_pharma_students = len(pharma_students)

    summary = {
        "higher_notes_count_pharma": len(pharma_higher),
        "lower_or_equal_notes_count_pharma": total_pharma_students - len(pharma_higher),
    }

    return {
        "summary": summary,
        "classement_general": f"{classement_general}/{total_students}",
        "classement_pharma": f"{classement_pharma}/{total_pharma_students}"
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    error = None
    if request.method == 'POST':
        try:
            # Fichier des résultats de la colle
            colle_file = request.files['colle']
            target_id = request.form['target_id']
            colle_path = os.path.join(app.root_path, 'static', secure_filename(colle_file.filename))
            colle_file.save(colle_path)
            
            # Comparer les résultats avec les données de la colle
            result = compare_notes_with_ue14_only(colle_path, target_id)
            
            # Supprimer les fichiers après traitement
            os.remove(colle_path)
        except Exception as e:
            error = str(e)
    
    return render_template('index.html', result=result, error=error)

if __name__ == '__main__':
    app.run(debug=True)
