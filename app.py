from flask import Flask, request, render_template, send_file, jsonify
import os
import google.generativeai as genai
from PIL import Image
import zipfile
import io
import base64

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "captions"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

import time
from google.api_core import exceptions

# Global variable to track requests (approximate, as retries may affect accuracy)
request_count = 0
daily_quota = 50

def generate_caption(image_path, api_key, trigger_word):
    global request_count
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-pro")
    try:
        img = Image.open(image_path).convert("RGB")
        print(f"Image opened: {image_path}, size: {img.size}, format: {img.format}, mode: {img.mode}")
        temp_path = image_path + ".temp.png"
        img.save(temp_path, "PNG", quality=95)
        img = Image.open(temp_path).convert("RGB")
        os.remove(temp_path)  # Clean up
        print(f"Image reprocessed: {image_path}, size: {img.size}, format: {img.format}, mode: {img.mode}")
    except Exception as e:
        print(f"Warning: Failed to process image {image_path}: {str(e)}")
        return None, False  # Return None caption and False quota_exceeded
    prompt = (
prompt = (
    "Generate a concise, keyword-rich caption for this image for LoRA training, assuming the subject is a beautiful 20-year-old woman. "
    "Start with the trigger word provided, if any, followed by a description of her facial expression, body pose and features, and clothing details (including any NSFW elements if present). "
    "Include surroundings and setting as secondary details, keeping the focus on the woman. "
    "Use factual language, keep the text short, and avoid structural tags or brackets."
    )
    max_retries = 3
    request_count += 1  # Increment counter for each new attempt
    print(f"Request count: {request_count}/{daily_quota}")
    quota_exceeded = False
    for attempt in range(max_retries + 1):
        try:
            time.sleep(60)  # Wait 60 seconds to respect daily quota and retry delay
            response = model.generate_content([prompt, img])
            print(f"Full response object: {response}")
            print(f"Response candidates: {response.candidates}")
            print(f"Safety ratings: {response.candidates[0].safety_ratings if response.candidates else 'No candidates'}")
            if not response or not response.candidates:
                raise Exception("No valid response or candidates from Gemini API")
            if not response.candidates[0].content.parts:
                print(f"Response parts: {response.candidates[0].content.parts}")
                print(f"Content details: {response.candidates[0].content}")
                print(f"Raw response: {response._result}")
                print(f"Finish reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")
                if response.candidates[0].safety_ratings:
                    print(f"Safety violations: {response.candidates[0].safety_ratings}")
                print(f"Attempt {attempt + 1}/{max_retries + 1} failed for {image_path}")
                return None, False  # Return None caption and False quota_exceeded
            for part in response.candidates[0].content.parts:
                print(f"Part content: {part.text if hasattr(part, 'text') else 'No text'}")
            caption = response.text.strip() if hasattr(response, 'text') else response.candidates[0].content.parts[0].text.strip()
            return caption, False  # Return caption and False quota_exceeded on success
        except exceptions.TooManyRequests as e:
            print(f"Error: Quota exceeded for {image_path} (Attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
            quota_exceeded = True
            print(f"Daily quota (50 requests) has been exceeded. Please wait until ~2:00 AM CEST for reset or use a new API key.")
            return None, True  # Return None caption and True quota_exceeded
        except Exception as e:
            print(f"Warning: API generation failed for {image_path} (Attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
            if attempt < max_retries:
                time.sleep(60)  # Wait before retrying
            else:
                return None, False  # Return None caption and False quota_exceeded after max retries
    if trigger_word and caption:
        caption = f"{trigger_word.strip()}, {caption}"
    return caption, quota_exceeded  # Ensure consistent return type

@app.route("/", methods=["GET", "POST"])
def index():
    global request_count
    request_count = 0  # Reset counter at the start of each session
    if request.method == "POST":
        files = request.files.getlist("images")
        api_key = request.form.get("api_key")
        trigger_word = request.form.get("trigger_word")
        if not api_key:
            return jsonify({"error": "Gemini API key is required."})
        if not files:
            return jsonify({"error": "At least one image is required."})
        captions = {}
        processed_images = []
        skipped_images = []
        quota_exceeded = False
        try:
            for file in files:
                if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
                    file.save(file_path)
                    caption, is_quota_exceeded = generate_caption(file_path, api_key, trigger_word)
                    print(f"Debug: File {file.filename}, caption: {caption}, is_quota_exceeded: {is_quota_exceeded}, quota_exceeded: {quota_exceeded}")
                    if caption is not None:  # Check if caption exists
                        captions[file.filename] = caption
                        txt_path = os.path.join(OUTPUT_FOLDER, os.path.splitext(file.filename)[0] + '.txt')
                        with open(txt_path, 'w', encoding='utf-8') as f:
                            f.write(caption)
                        processed_images.append({"image": file.filename, "txt": os.path.basename(txt_path)})
                    else:
                        skipped_images.append(file.filename)
                    if is_quota_exceeded:
                        quota_exceeded = True  # Set immediately on first quota exceedance
                    # Ensure quota_exceeded is set if all images are skipped due to quota
                    if request_count >= daily_quota or (len(skipped_images) == len(files) and skipped_images):
                        quota_exceeded = True
            print(f"Debug: Final quota_exceeded: {quota_exceeded}, skipped_images: {skipped_images}, processed_images: {processed_images}")
            if not processed_images and not skipped_images:
                raise Exception("No images were processed or skipped due to errors.")
            result = {"error": None, "processed_images": processed_images, "skipped_images": skipped_images, "zip_data": None, "quota_exceeded": quota_exceeded}
            if processed_images:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for filename in os.listdir(OUTPUT_FOLDER):
                        file_path = os.path.join(OUTPUT_FOLDER, filename)
                        if os.path.isfile(file_path):
                            print(f"Writing {file_path} to zip")
                            zip_file.write(file_path, filename)
                zip_buffer.seek(0)
                print(f"Zip buffer size: {zip_buffer.getbuffer().nbytes}")
                if zip_buffer.getbuffer().nbytes == 0:
                    raise Exception("Zip buffer is empty, no files were written")
                result["zip_data"] = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)})
    return render_template("index.html", error=None)
if __name__ == "__main__":
    app.run(debug=True)