from flask import Flask, request, render_template, send_file
    import os
    import google.generativeai as genai
    from PIL import Image
    import zipfile
    import io

    app = Flask(__name__)
    UPLOAD_FOLDER = "uploads"
    OUTPUT_FOLDER = "captions"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    def generate_caption(image_path, api_key, trigger_word):
        """Generate a caption for a single image using Gemini with a trigger word."""
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-pro")
        img = Image.open(image_path).convert("RGB")
        prompt = "Describe this image in detail for use in AI model training, focusing on style, subject, and background."
        response = model.generate_content([prompt, img])
        caption = response.text.strip()
        if trigger_word:
            caption = f"{trigger_word.strip()}, {caption}"
        return caption

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            files = request.files.getlist("images")
            api_key = request.form.get("api_key")
            trigger_word = request.form.get("trigger_word")
            
            if not api_key:
                return render_template("index.html", error="Gemini API key is required.")
            if not files:
                return render_template("index.html", error="At least one image is required.")

            captions = {}
            try:
                for file in files:
                    if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
                        file.save(file_path)
                        caption = generate_caption(file_path, api_key, trigger_word)
                        captions[file.filename] = caption
                        txt_path = os.path.join(OUTPUT_FOLDER, os.path.splitext(file.filename)[0] + '.txt')
                        with open(txt_path, 'w', encoding='utf-8') as f:
                            f.write(caption)
                
                # Create a zip file of captions
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for filename in os.listdir(OUTPUT_FOLDER):
                        zip_file.write(os.path.join(OUTPUT_FOLDER, filename), filename)
                zip_buffer.seek(0)
                return send_file(zip_buffer, download_name="captions.zip", as_attachment=True)
            except Exception as e:
                return render_template("index.html", error=f"Error: {str(e)}")
        
        return render_template("index.html", error=None)

    if __name__ == "__main__":
        app.run(debug=True)