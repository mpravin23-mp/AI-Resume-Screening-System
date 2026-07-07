from utils.skills import SKILLS

def compare_skills(resume_text, job_text):

    comparison = []

    matched = 0

    for skill in SKILLS:

        resume_has = skill.lower() in resume_text.lower()

        job_has = skill.lower() in job_text.lower()

        if job_has:

            if resume_has:
                matched += 1

            comparison.append({

                "skill": skill.title(),

                "resume": resume_has,

                "job": job_has,

                "matched": resume_has and job_has

            })

    return comparison, matched