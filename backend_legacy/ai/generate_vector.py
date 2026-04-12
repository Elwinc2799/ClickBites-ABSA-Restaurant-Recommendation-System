# Import necessary libraries and modules for data processing and analysis
from collections import Counter, defaultdict
import torch
import pickle
import re
import random
import os
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# SpaCy library for natural language processing tasks
import spacy

# Transformers from HuggingFace for BERT model
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# VaderSentiment library for sentiment analysis
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Set the seed for the random number generator
random_seed = 42
random.seed(random_seed)

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Load the fine-tuned model and tokenizer
model_path = "./ai/fine_tuned_model"
model = AutoModelForSequenceClassification.from_pretrained(model_path)

# Initialize tokenizer
model_used = "bert-large-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_used)

# Load the label encoder
with open("./ai/label_encoder.pkl", "rb") as f:
    label_encoder = pickle.load(f)

print("Loading the model...")

# Initialize the VADER sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# Get the absolute path of the current script
script_dir = os.path.dirname(os.path.realpath(__file__))

# Construct the NLTK data path
nltk_data_path = os.path.join(script_dir, "nltk_data")

# Download the NLTK data
nltk.download("punkt", download_dir=nltk_data_path)
nltk.download("stopwords", download_dir=nltk_data_path)
stop_words = set(stopwords.words("english"))


# Function to make predictions
def predict_category(target, threshold=0.5):
    inputs = tokenizer(target, return_tensors="pt", padding=True, truncation=True)

    logits = model(**inputs).logits
    probabilities = torch.softmax(logits, dim=1)
    max_probability, predicted_class_idx = torch.max(probabilities, dim=1)

    # Check if the max probability is below the threshold, if yes, assign the category "none"
    if max_probability.item() < threshold:
        return "none"

    predicted_class = label_encoder.inverse_transform([predicted_class_idx.numpy()[0]])[0]
    return predicted_class


# Extract nouns and adjectives from each sentence
def extract_nouns_and_adjectives(sentence):
    doc = nlp(sentence)

    # Extract monetary values
    money_entities = []
    for ent in doc.ents:
        if ent.label_ == "MONEY":
            # Combine dollar sign and number, if applicable
            if ent.text.startswith("$"):
                money_entities.append(ent.text)
            else:
                preceding_token = doc[ent.start - 1]
                if preceding_token.text == "$":
                    money_entities.append("$" + ent.text)
                else:
                    money_entities.append(ent.text)

    # Extract noun phrases
    noun_phrases = [chunk.text for chunk in doc.noun_chunks]

    # Combine the two lists
    return money_entities + noun_phrases


# Function to predict category given a specific target
def predict_categories(sentence):
    targets = list(set(extract_nouns_and_adjectives(sentence)))
    targets.sort(key=len, reverse=True)
    categories = {}

    for target in targets:
        predicted_category = predict_category(target)
        target_start = -1
        for match in re.finditer(r"\b" + re.escape(target) + r"\b", sentence):
            target_start = match.start()
            target_end = match.end()

            if target_start == -1:
                break
            if predicted_category not in categories:
                categories[predicted_category] = [(target, target_start, target_end)]
            else:
                match_found = False
                for key in categories:
                    for value in categories[key]:
                        if target_start >= value[1] and target_end <= value[2]:
                            match_found = True
                if not match_found:
                    categories[predicted_category].append((target, target_start, target_end))

    return categories


# Extract a phrase surrounding the target word
def extract_phrase(sentence, start, end, pred_phrase):
    target = sentence[start:end].split(" ")
    words = re.findall(r"\w+", sentence)
    indices = [(m.start(), m.end()) for m in re.finditer(r"\w+", sentence)]

    # Check if length of sentence too short
    if len(words) < (len(pred_phrase.split(" ")) + 4):
        return pred_phrase
    else:
        for i, (word_start, word_end) in enumerate(indices):
            if start == word_start:
                phrase_start = max(0, i - 2)  # taking in 2 words before the target word
                phrase_end = min(len(words), i + len(target) + 3)  # taking in 2 words after the target word
                phrase = " ".join(words[phrase_start:phrase_end])
                return phrase

        return ""


def process_review_text(review_text):
    categories_scores = {"food": [], "service": [], "price": [], "ambience": [], "misc": []}

    # Tokenize the review text into sentences
    sentences = re.split("[.!?]", review_text)

    values_to_replace = ["\\n\\n", "\\n", "\n", "\n\n"]

    for i in range(len(sentences)):
        for value in values_to_replace:
            sentences[i] = sentences[i].replace(value, "")

        sentences[i] = sentences[i].strip()

    # Remove any empty sentences
    sentences = [sentence for sentence in sentences if sentence]

    # Process each sentence
    for sentence in sentences:
        ### STOPWORD REMOVAL ###
        tokenized_sentence = word_tokenize(sentence)
        sentence = " ".join([word for word in tokenized_sentence if word not in stop_words])

        # Predict categories for the given sentence
        predicted_categories = predict_categories(sentence)

        # Get the predicted polarity label for each predicted category
        for category, target_list in predicted_categories.items():
            # Ignore all 'none' category target
            if category != "none":
                for pred_target, pred_from_idx, pred_to_idx in target_list:
                    phrase = extract_phrase(sentence, pred_from_idx, pred_to_idx, pred_target)
                    sentiment_scores = analyzer.polarity_scores(phrase)

                    polarity = sentiment_scores["compound"]

                    if polarity >= 0.05:
                        predicted_polarity = "positive"
                    elif polarity <= -0.05:
                        predicted_polarity = "negative"
                    else:
                        predicted_polarity = "neutral"

                    categories_scores[category].append(polarity)

    # Calculate average sentiment scores for each category in each review
    average_scores = {}
    for category, scores in categories_scores.items():
        if scores:
            average_scores[category] = sum(scores) / len(scores)
        else:
            average_scores[category] = 0

    # Create a 5D vector for the review
    vector = [
        average_scores["food"],
        average_scores["service"],
        average_scores["price"],
        average_scores["ambience"],
        average_scores["misc"],
    ]
    return vector


# Function to convert review text to vector and accumulate vectors
def generate_vector(text):
    vector = process_review_text(text)
    return vector


# # Main function
# if __name__ == "__main__":
#     vector = generate_vector(
#         """
#     Sushi Hatchi has been in my list for a long time and I was excited to finally give it a try! It was easy to get a reservation online, and when we got there we were seated immediately even though the restaurant was packed! It's a cute ambiance, with plenty of tables in a long row home style space.

#     I thought the prices were definitely reasonable and their menu has a lot of different options I hadn't tried before. You had the option of wait service, or just ordering and paying online using a QR code.

#     We decided to try an assortment of items from different parts of the menu. My first experience with chicken Cara-age was delish, especially with the tartar sauce. The tempura udon noodle was maybe one of my favorite dishes - lots of noodles, rich flavorful broth, and yummy shrimp tempura on the side. The Capitol roll was delicious - as with anything deep fried. Usually, I'm not a fan of cream cheese in a roll, but paired with the sugary sauce and melted inside, this one was a hit. The volcano roll came highly recommended, and the Alaska roll intrigued us with the onion sauce addition. Along with a classic tuna nigiri, we also tried the prime beef nigiri.

#     Overall, a very interesting dining experience. There were a lot of flavors I've never had combined before, and wouldn't think to combine. For example, that "onion sauce" on top of the Alaska roll is really similar to pico de gallo ... an interesting flavor combined with a raw fish and sushi roll. Sriracha in the volcano roll and sugar grains in the "sweet miso" sauce on the Capitol roll were pleasant surprises, but unusual nonetheless. Overall, I would love to come back and try more, but be prepared this is not your typical Japanese spot!"""
#     )
#     print(vector)
