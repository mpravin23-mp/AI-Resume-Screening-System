def calculate_ats_score(comparison, resume_text):

    score = 0

    breakdown = {}

    total_skills = len(comparison)
    matched = sum(1 for item in comparison if item["matched"])

    # Technical Skills (50 Marks)
    if total_skills:
        technical = round((matched / total_skills) * 50, 2)
    else:
        technical = 0

    score += technical
    breakdown["technical"] = technical

    resume = resume_text.lower()

    # Education (20 Marks)
    education = 0
    if "bachelor" in resume or "computer science" in resume:
        education = 20

    score += education
    breakdown["education"] = education

    # Experience (15 Marks)
    experience = 0
    if "experience" in resume or "year" in resume:
        experience = 15

    score += experience
    breakdown["experience"] = experience

    # Projects (10 Marks)
    projects = 0
    if "project" in resume:
        projects = 10

    score += projects
    breakdown["projects"] = projects

    # Certifications (5 Marks)
    certification = 0
    if "certificate" in resume or "certification" in resume:
        certification = 5

    score += certification
    breakdown["certification"] = certification

    breakdown["total"] = round(score, 2)

    return breakdown