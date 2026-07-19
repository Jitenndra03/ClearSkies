import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv('.env')
engine = create_engine(os.environ.get('DATABASE_URL'))
with engine.connect() as conn:
    res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
    print([r[0] for r in res])
