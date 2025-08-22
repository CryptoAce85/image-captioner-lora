# Bulk Image Captioner for LoRA Training


  A Flask-based web app for generating image captions for LoRA training, using the Gemini-2.5-pro model. Users can input their Gemini API key and a custom trigger word via the web interface.

  ## Features
  - Upload multiple images (.png, .jpg, .jpeg) and generate detailed captions.
  - Specify a trigger word (e.g., "skw style") for LoRA training.
  - Provide your Gemini API key securely through the web interface.
  - Download captions as a `.zip` file with `.txt` files matching image names.

  ## Setup Locally
  1. Clone the repository:
     ```bash
     git clone https://github.com/CryptoAce85/image-captioner-lora.git
     cd image-captioner-lora
     ```
  2. Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```
  3. Run the app:
     ```bash
     python app.py
     ```
     Access at `http://127.0.0.1:5000`.

  ## Deployment on GratisVPS.net Free VPS (Aurora Plan)
  
  1. Sign up for a free Linux VPS at [GratisVPS.net](https://gratisvps.net) and claim the Aurora plan (beta test, 120 days) [Web:5].
     - Specs: 16GB RAM (DDR5), 8 AMD Ryzen Cores, 240GB NVMe Space, 20 TB Bandwidth (2Gbit), 17Tbps Anti-DDoS Protection.
	 
  2. Select **Ubuntu 22.04 LTS** during setup.
  
  3. SSH into the VPS:
     ```bash
     ssh username@your-vps-ip
	 ``` 
	 
  4. Install dependencies:
     ```bash
     sudo apt update
     sudo apt install -y python3 python3-pip git nginx
     pip3 install --user gunicorn
     git clone https://github.com/CryptoAce85/image-captioner-lora.git
     cd image-captioner-lora
     pip3 install -r requirements.txt
     ```
  5. Set up Gunicorn:
     ```bash
     sudo nano /etc/systemd/system/captioner.service
     ```
     Add:
     ```
     [Unit]
     Description=Bulk Image Captioner Flask App
     After=network.target

     [Service]
     User=your-username
     WorkingDirectory=/home/your-username/image-captioner-lora
     ExecStart=/home/your-username/.local/bin/gunicorn --bind 0.0.0.0:8000 app:app
     Restart=always

     [Install]
     WantedBy=multi-user.target
     ```
     Enable and start:
     ```bash
     sudo systemctl enable captioner
     sudo systemctl start captioner
     ```
  6. Configure Nginx:
     ```bash
     sudo nano /etc/nginx/sites-available/default
     ```
     Add:
     ```
     server {
         listen 80;
         server_name _;
         location / {
             proxy_pass http://127.0.0.1:8000;
             proxy_set_header Host $host;
             proxy_set_header X-Real-IP $remote_addr;
         }
     }
     ```
     Restart Nginx: `sudo systemctl restart nginx`.
  7. Allow HTTP traffic:
     ```bash
     sudo ufw allow 80
     sudo ufw enable
     ```
  8. Access at `http://your-vps-ip`.

  ## Usage
  1. Visit the web app.
  2. Enter your Gemini API key (from https://makersuite.google.com).
  3. (Optional) Enter a trigger word (e.g., "skw style").
  4. Upload images and click "Generate Captions".
  5. Download `captions.zip` for LoRA training.

  ## Notes
  - Requires Python 3.8+ and a Gemini API key.
  - Free tier is a 120-day beta test (valid until ~Dec 20, 2025); monitor for changes [Web:5].
  - Aurora's 16GB RAM and 8 cores support moderate to high use [Web:4].
  - Check reliability, as it's a beta service [Web:2].
  - Clean up `uploads/` and `captions/` if needed:
    ```bash
    rm -rf ~/image-captioner-lora/uploads/* ~/image-captioner-lora/captions/*
    ```

  ## License
  
  MIT License