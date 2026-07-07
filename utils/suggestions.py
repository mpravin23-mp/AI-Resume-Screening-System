def generate_suggestions(comparison, resume_text):

    suggestions = []
    missing = []

    for item in comparison:
        if not item["matched"]:
            missing.append(item["skill"])
            suggestions.append("Improve " + item["skill"])

    if "project" not in resume_text.lower():
        suggestions.append("Add projects")

    if "github" not in resume_text.lower():
        suggestions.append("Add GitHub link")

    return missing, suggestions