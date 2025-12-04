from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PIPEDREAM_URL = os.getenv("PIPEDREAM_URL")

def search_supabase(query):
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    body = {"query_text": query, "match_count": 5}
    r = requests.post(url, json=body, headers=headers)
    r.raise_for_status()
    return r.json()

def summarize_with_openai(query, docs):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""
    Summarize the following search results into 3–4 sentences.
    User query: {query}
    Documents: {docs}
    """
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 250,
        "temperature": 0.2
    }
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def log_to_pipedream(data):
    try:
        requests.post(PIPEDREAM_URL, json=data, timeout=2)
    except:
        pass

@app.post("/search")
def search():
    data = request.get_json()
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Query missing"}), 400

    try:
        docs = search_supabase(query)
        answer = summarize_with_openai(query, docs)
        log_to_pipedream({"query": query, "results": len(docs)})
        return jsonify({"answer": answer, "raw_results": docs})
    except Exception as e:
        log_to_pipedream({"error": str(e), "query": query})
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=8000, debug=True)
