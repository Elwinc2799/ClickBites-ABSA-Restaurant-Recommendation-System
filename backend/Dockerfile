FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (avoids downloading 2GB CUDA build)
RUN pip install --no-cache-dir torch==2.10.0 --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
COPY requirements.txt .
RUN grep -v '^torch' requirements.txt > requirements_no_torch.txt && \
    pip install --no-cache-dir -r requirements_no_torch.txt huggingface_hub

# Download spacy model (direct URL avoids version-resolution issues)
RUN pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# Copy application code
COPY . .

# Download NLTK data
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"

# Model downloaded at container startup via start.sh (needs HF_TOKEN runtime secret)
EXPOSE 7860

CMD ["/bin/bash", "start.sh"]
