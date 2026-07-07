from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_pdf(file_path, data):

    c = canvas.Canvas(file_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)

    c.drawString(50, 750, "AI Resume ATS Report")

    c.setFont("Helvetica", 11)

    y = 720

    c.drawString(50, y, f"File Name: {data['file_name']}")
    y -= 20

    c.drawString(50, y, f"ATS Score: {data['ats_score']}%")
    y -= 20

    c.drawString(50, y, f"TF-IDF Score: {data['tfidf_score']}%")
    y -= 20

    c.drawString(50, y, "Recommendation:")
    y -= 20
    c.drawString(70, y, data['recommendation']['status'])

    y -= 30
    c.drawString(50, y, "Missing Skills:")
    y -= 20

    for skill in data['missing_skills']:
        c.drawString(70, y, f"- {skill}")
        y -= 15

    c.save()