"""
setup_env.py  –  One-time helper to create your .env file.
Run once: python setup_env.py
"""
import os

ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')

DEFAULT_ENV = """SECRET_KEY=studymate-dev-secret-key-2024-change-in-prod
DATABASE_URL=postgresql+psycopg2://postgres:Suma21@localhost:5432/studymate_db
FLASK_ENV=development
FLASK_DEBUG=1
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=uploads

# IBM watsonx AI  –  get free credentials at https://cloud.ibm.com/watsonx
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-13b-instruct-v2
"""

if os.path.exists(ENV_FILE):
    print(f'.env already exists at {ENV_FILE}')
    print('Delete it first if you want to reset it.')
else:
    with open(ENV_FILE, 'w') as f:
        f.write(DEFAULT_ENV)
    print(f'.env created at {ENV_FILE}')
    print('Edit it to add your WATSONX_API_KEY and WATSONX_PROJECT_ID for AI features.')
    print('The app will work without them for all non-AI features.')
