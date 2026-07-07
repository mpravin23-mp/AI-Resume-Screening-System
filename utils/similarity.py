from sklearn.metrics.pairwise import cosine_similarity

def calculate_similarity(vectors):
    similarity = cosine_similarity(vectors[0:1], vectors[1:2])
    return similarity[0][0] * 100