"""
app/services/watsonx_service.py

IBM watsonx AI service layer.
Handles all LLM calls: summarization, quiz generation,
flashcard creation, RAG chat, and study plan generation.

Requires in .env:
    WATSONX_API_KEY   – IBM Cloud API key
    WATSONX_PROJECT_ID – watsonx.ai project ID
    WATSONX_URL        – regional endpoint (default: us-south)
"""
import os
import json
import re
from typing import Optional

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams


# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_model: Optional[ModelInference] = None


def _get_model() -> ModelInference:
    global _model
    if _model is not None:
        return _model

    # Read from environment (loaded from .env by config.py at startup)
    api_key    = os.environ.get('WATSONX_API_KEY', '').strip()
    project_id = os.environ.get('WATSONX_PROJECT_ID', '').strip()
    url        = os.environ.get('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com').strip()
    model_id   = os.environ.get('WATSONX_MODEL_ID', 'ibm/granite-13b-instruct-v2').strip()

    if not api_key or not project_id:
        raise ValueError(
            'IBM watsonx AI is not configured. '
            'Add WATSONX_API_KEY and WATSONX_PROJECT_ID to your .env file. '
            'Get free credentials at https://cloud.ibm.com/watsonx'
        )

    credentials = Credentials(url=url, api_key=api_key)
    _model = ModelInference(
        model_id=model_id,
        credentials=credentials,
        project_id=project_id,
        params={
            GenParams.MAX_NEW_TOKENS: 1500,
            GenParams.MIN_NEW_TOKENS: 10,
            GenParams.TEMPERATURE: 0.3,
            GenParams.TOP_P: 0.9,
            GenParams.REPETITION_PENALTY: 1.1,
        }
    )
    return _model


def _generate(prompt: str, max_tokens: int = 1500) -> str:
    """Core generate call with a custom token cap."""
    model = _get_model()
    result = model.generate_text(
        prompt=prompt,
        params={
            GenParams.MAX_NEW_TOKENS: max_tokens,
            GenParams.TEMPERATURE: 0.3,
            GenParams.TOP_P: 0.9,
            GenParams.REPETITION_PENALTY: 1.1,
        }
    )
    return result.strip() if isinstance(result, str) else str(result).strip()


# ---------------------------------------------------------------------------
# 1. Summarization
# ---------------------------------------------------------------------------

def generate_summary(text: str, title: str = '') -> str:
    """
    Generate an exam-oriented summary with key topics highlighted.
    Returns markdown-formatted text.
    """
    # Use first 4000 chars to stay within token limits
    excerpt = text[:4000]
    doc_ref = f'"{title}"' if title else 'the document'

    prompt = f"""You are an expert academic tutor helping students prepare for exams.

Read the following study material from {doc_ref} and produce a well-structured, exam-oriented summary.

Format your response EXACTLY as:
## Key Concepts
- [list the 5-7 most important concepts]

## Summary
[3-5 paragraph summary covering all major topics, written clearly for a student]

## Important Points to Remember
- [6-10 bullet points of facts, definitions, or formulas a student must know for an exam]

## Key Terms
- **Term**: Definition
[list 4-6 key terms with definitions]

STUDY MATERIAL:
{excerpt}

Begin your structured summary now:"""

    return _generate(prompt, max_tokens=1200)


# ---------------------------------------------------------------------------
# 2. Quiz Generation
# ---------------------------------------------------------------------------

def generate_quiz(text: str, num_questions: int = 5, title: str = '') -> list[dict]:
    """
    Generate multiple-choice quiz questions.
    Returns list of dicts: {question, option_a, option_b, option_c, option_d, correct_answer, explanation, topic}
    """
    excerpt = text[:3500]
    doc_ref = f'"{title}"' if title else 'the document'

    prompt = f"""You are an expert exam question writer.

Based on the study material from {doc_ref}, generate exactly {num_questions} multiple-choice questions.

Output ONLY valid JSON — a JSON array with no extra text before or after.
Each item must have these exact keys:
  "question": string,
  "option_a": string,
  "option_b": string,
  "option_c": string,
  "option_d": string,
  "correct_answer": "A" or "B" or "C" or "D",
  "explanation": string (1-2 sentences explaining why),
  "topic": string (short topic label)

STUDY MATERIAL:
{excerpt}

JSON array:"""

    raw = _generate(prompt, max_tokens=1800)
    return _parse_json_array(raw, num_questions)


# ---------------------------------------------------------------------------
# 3. Flashcard Generation
# ---------------------------------------------------------------------------

def generate_flashcards(text: str, num_cards: int = 8, title: str = '') -> list[dict]:
    """
    Generate flashcards (front/back pairs).
    Returns list of dicts: {front, back, difficulty}
    """
    excerpt = text[:3000]

    prompt = f"""You are a study coach creating digital flashcards.

Based on the study material below, generate exactly {num_cards} flashcards.

Output ONLY valid JSON — a JSON array, no extra text.
Each item must have:
  "front": string (a question or term, max 15 words),
  "back": string (the answer or definition, 1-3 sentences),
  "difficulty": "easy" or "medium" or "hard"

STUDY MATERIAL:
{excerpt}

JSON array:"""

    raw = _generate(prompt, max_tokens=1200)
    return _parse_json_array(raw, num_cards)


# ---------------------------------------------------------------------------
# 4. RAG Chat
# ---------------------------------------------------------------------------

def chat_with_document(question: str, context_chunks: list[str],
                        chat_history: list[dict] = None) -> str:
    """
    Answer a student question using provided document context (RAG).
    chat_history: list of {role: 'user'|'assistant', content: str}
    """
    context = '\n\n---\n\n'.join(context_chunks[:4])  # top 4 chunks

    history_text = ''
    if chat_history:
        for msg in chat_history[-4:]:  # last 4 exchanges
            role = 'Student' if msg['role'] == 'user' else 'Tutor'
            history_text += f'{role}: {msg["content"]}\n'

    prompt = f"""You are an intelligent AI tutor helping a student understand their study material.
Answer ONLY based on the provided document context. If the answer is not in the context, say so clearly.
Be concise, clear, and educational. Use examples when helpful.

DOCUMENT CONTEXT:
{context}

{f'PREVIOUS CONVERSATION:{chr(10)}{history_text}' if history_text else ''}
Student: {question}
Tutor:"""

    return _generate(prompt, max_tokens=600)


# ---------------------------------------------------------------------------
# 5. Study Plan Generation
# ---------------------------------------------------------------------------

def generate_study_plan(title: str, subject: str, goal: str,
                         duration_days: int, difficulty: str,
                         topics: list[str] = None) -> str:
    """
    Generate a personalized study plan in markdown.
    """
    topics_str = ', '.join(topics[:8]) if topics else 'general topics from the subject'
    diff_map = {'easy': 'light (1-2 hours/day)', 'medium': 'moderate (2-3 hours/day)',
                'hard': 'intensive (3-5 hours/day)'}
    intensity = diff_map.get(difficulty, 'moderate (2-3 hours/day)')

    prompt = f"""You are an expert academic study coach.

Create a detailed, realistic {duration_days}-day study plan for a student with these details:
- Subject: {subject or 'General Study'}
- Goal: {goal or 'Master the subject for exams'}
- Difficulty: {difficulty} ({intensity})
- Key topics to cover: {topics_str}

Format your response EXACTLY as:

## Study Plan: {title}

### Overview
[2-3 sentences describing the plan strategy]

### Weekly Breakdown
**Week 1:** [theme and focus]
- Day 1-2: [specific tasks]
- Day 3-4: [specific tasks]
- Day 5-7: [specific tasks + review]

[Continue for each week up to {min(duration_days // 7 + 1, 4)} weeks]

### Daily Study Tips
- [4-5 actionable tips for success]

### Recommended Resources
- [3-4 specific resource suggestions]

### Milestones & Self-Assessment
- Week 1: [what to have achieved]
- Week 2: [what to have achieved]
[continue...]

Generate the full plan now:"""

    return _generate(prompt, max_tokens=1400)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_array(raw: str, expected_count: int) -> list[dict]:
    """Extract and parse a JSON array from LLM output."""
    # Find the first '[' and last ']'
    start = raw.find('[')
    end = raw.rfind(']')
    if start == -1 or end == -1:
        return []
    json_str = raw[start:end + 1]

    # Fix common LLM JSON mistakes
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)  # trailing commas
    json_str = re.sub(r'[\x00-\x1f]', ' ', json_str)    # control chars

    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return data[:expected_count]
    except json.JSONDecodeError:
        pass
    return []


def is_configured() -> bool:
    """Return True if watsonx credentials are present in environment."""
    return bool(os.environ.get('WATSONX_API_KEY') and
                os.environ.get('WATSONX_PROJECT_ID'))
