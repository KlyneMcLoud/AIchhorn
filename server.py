from flask import Flask, request, jsonify
from llama_cpp import Llama

app = Flask(__name__)
llm = Llama(
    model_path="C:\\usr\\dev\\llmodels\\mistral-7b-openorca.Q4_K_M.gguf",
    n_ctx=4096,
    n_gpu_layers=-1,
    n_threads=6,
    use_mlock=True
)

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    prompt = data.get("prompt", "")
    output = llm(prompt, max_tokens=128)
    return jsonify(output)

if __name__ == "__main__":
    app.run(port=5000)
