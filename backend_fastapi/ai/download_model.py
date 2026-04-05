"""
Download model artifacts from HF Hub at container startup.
Run this before starting the server if local model files are absent.
"""
import os
from pathlib import Path

def download_if_needed():
    ai_dir = Path(__file__).parent
    model_dir = ai_dir / "fine_tuned_model"
    label_encoder_path = ai_dir / "label_encoder.pkl"

    hf_model_id = os.getenv("HF_MODEL_ID", "Elwinc2799/clickbites-absa-bert")
    hf_token = os.getenv("HF_TOKEN")

    needs_model = not model_dir.exists() or not any(model_dir.iterdir())
    needs_encoder = not label_encoder_path.exists()

    if not needs_model and not needs_encoder:
        print("Model files already present, skipping download.")
        return

    from huggingface_hub import hf_hub_download, snapshot_download

    if needs_model:
        print(f"Downloading model from {hf_model_id}...")
        snapshot_download(
            repo_id=hf_model_id,
            local_dir=str(model_dir),
            token=hf_token,
            ignore_patterns=["*.pkl"]
        )
        print("Model downloaded.")

    if needs_encoder:
        print("Downloading label_encoder.pkl...")
        hf_hub_download(
            repo_id=hf_model_id,
            filename="label_encoder.pkl",
            local_dir=str(ai_dir),
            token=hf_token
        )
        print("Label encoder downloaded.")


if __name__ == "__main__":
    download_if_needed()
