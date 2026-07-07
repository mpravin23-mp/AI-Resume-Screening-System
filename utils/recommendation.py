def get_recommendation(score):

    if score >= 85:

        return {
            "status":"Excellent Match",
            "color":"success",
            "message":"The candidate is highly suitable for this position."
        }

    elif score >= 70:

        return {
            "status":"Good Match",
            "color":"primary",
            "message":"The candidate meets most job requirements."
        }

    elif score >= 50:

        return {
            "status":"Average Match",
            "color":"warning",
            "message":"Candidate should improve a few missing skills."
        }

    else:

        return {
            "status":"Low Match",
            "color":"danger",
            "message":"Candidate should gain more relevant skills."
        }   