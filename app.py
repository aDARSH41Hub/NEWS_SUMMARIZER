import os
import re
import string
from collections import Counter

from dotenv import load_dotenv
load_dotenv()

import nltk
import streamlit as st
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from openai import OpenAI

# ---------------------------------------------------------------------------
# LLM client setup (OpenAI-compatible, pointed at OpenRouter)
# ---------------------------------------------------------------------------
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY") or "no-key-set-yet",
)
MODEL = "deepseek/deepseek-chat"  # swap for any OpenRouter model you have credit for


def call_llm(prompt: str, system: str = "You are a precise, factual assistant.") -> str:
    """Single shared LLM call wrapper -- every LLM-backed objective routes through here."""
    if not os.environ.get("OPENROUTER_API_KEY"):
        return "[No API key set -- add OPENROUTER_API_KEY to your environment to enable this feature.]"
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def preprocess(text: str) -> dict:
    """
    Classical NLP preprocessing -- done WITHOUT an LLM, using NLTK directly.
    This is deliberately separate from the LLM calls below: it demonstrates
    actual NLP technique, not just prompt engineering.
    """
    sentences = sent_tokenize(text)
    words = word_tokenize(text.lower())

    stop_words = set(stopwords.words("english"))
    cleaned_words = [
        w for w in words
        if w not in stop_words and w not in string.punctuation and w.isalpha()
    ]

    return {
        "sentence_count": len(sentences),
        "word_count": len(words),
        "cleaned_word_count": len(cleaned_words),
        "sentences": sentences,
        "cleaned_words": cleaned_words,
    }



def extract_keywords(cleaned_words: list, top_n: int = 10) -> list:
    """
    Frequency-based keyword extraction on preprocessed text.
    Simple, explainable, no extra dependencies -- exactly the kind of
    technique you should be able to explain line-by-line if asked.
    """
    freq = Counter(cleaned_words)
    return freq.most_common(top_n)



def summarize(text: str) -> str:
    prompt = (
        "Summarize the following news article in 3-4 concise sentences. "
        "Capture only the most important facts -- who, what, when, where, why. "
        "Do not add opinions or information not present in the article.\n\n"
        f"Article:\n{text}"
    )
    return call_llm(prompt)


# ---------------------------------------------------------------------------
#  Detect sentiment (LLM + prompt engineering)
# ---------------------------------------------------------------------------
def analyze_sentiment(text: str) -> str:
    prompt = (
        "Classify the overall sentiment of this news article as exactly one of: "
        "Positive, Negative, or Neutral. "
        "Then give a one-sentence justification. "
        "Format your answer as:\nSentiment: <label>\nReason: <one sentence>\n\n"
        f"Article:\n{text}"
    )
    return call_llm(prompt)


# ---------------------------------------------------------------------------
# Generate question-answer responses (LLM + prompt engineering)
# ---------------------------------------------------------------------------
def answer_question(text: str, question: str) -> str:
    prompt = (
        "Answer the question using ONLY information from the article below. "
        "If the answer is not present in the article, say so explicitly rather "
        "than guessing.\n\n"
        f"Article:\n{text}\n\nQuestion: {question}\nAnswer:"
    )
    return call_llm(prompt)


# ---------------------------------------------------------------------------
#  Interactive web interface
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="News NLP Analyzer", layout="wide")

    st.title("📰 Intelligent News Summarization & Sentiment Analysis")
    with st.sidebar:
        st.title("Project Info")
        st.markdown("""
    **Intelligent News Summarization and Sentiment Analysis**
    **Technologies Used**
    - Python
    - Streamlit
    - NLTK
    - OpenRouter API
    - DeepSeek Chat

    **Developed By**
    Adarsh Pratap Singh
    """)
    st.caption(
        "NLP preprocessing (NLTK) + LLM-powered summarization, sentiment analysis and question answering"
    )

    # -----------------------------
    # Session State Initialization
    # -----------------------------
    defaults = {
        "analysis_done": False,
        "article": "",
        "prep": None,
        "keywords": [],
        "summary": "",
        "sentiment": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # -----------------------------
    # Input
    # -----------------------------
    article_text = st.text_area(
        "Paste a news article below:",
        value=st.session_state.article,
        height=250,
    )

    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        analyze_clicked = st.button("Analyze")

    with col_btn2:
        clear_clicked = st.button("Clear")

    # -----------------------------
    # Clear Button
    # -----------------------------
    if clear_clicked:
        for key, value in defaults.items():
            st.session_state[key] = value

        st.rerun()

    # -----------------------------
    # Analyze
    # -----------------------------
    if analyze_clicked:

        if not article_text.strip():
            st.warning("Please paste a news article first.")
            st.stop()

        with st.spinner("Analyzing article..."):

            st.session_state.article = article_text

            st.session_state.prep = preprocess(article_text)

            st.session_state.keywords = extract_keywords(
                st.session_state.prep["cleaned_words"]
            )

            st.session_state.summary = summarize(article_text)

            st.session_state.sentiment = analyze_sentiment(article_text)

            st.session_state.analysis_done = True

    # -----------------------------
    # Display Results
    # -----------------------------
    if st.session_state.analysis_done:

        prep = st.session_state.prep

        col1, col2 = st.columns(2)

        with col1:

            st.subheader("1. NLP Preprocessing")

            st.write(f"**Sentences:** {prep['sentence_count']}")
            st.write(f"**Total words:** {prep['word_count']}")
            st.write(
                f"**Content words:** {prep['cleaned_word_count']}"
            )

            st.subheader("2. Extracted Keywords")

            for word, count in st.session_state.keywords:
                st.write(f"• **{word}** ({count})")

        with col2:

            st.subheader("3. Summary")
            st.write(st.session_state.summary)

            st.subheader("4. Sentiment Analysis")
            st.write(st.session_state.sentiment)

        st.divider()

        # -----------------------------
        # Question Answering
        # -----------------------------
        st.subheader("5. Ask Questions About This Article")

        with st.form("qa_form"):

            question = st.text_input(
                "Enter your question:"
            )

            ask = st.form_submit_button("Get Answer")

        if ask:

            if not question.strip():
                st.warning("Please enter a question.")

            else:

                with st.spinner("Generating answer..."):

                    answer = answer_question(
                        st.session_state.article,
                        question,
                    )

                st.success(answer)
st.divider()
st.caption("Built using Python, NLTK, Streamlit and OpenRouter")
if __name__ == "__main__":
    main()
