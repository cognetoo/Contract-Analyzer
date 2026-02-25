from api.db import engine
from api.models import Base

def init_db():
    Base.metadata.create_all(bind = engine)

if __name__ =="__main__":
    init_db()
    print("DB tables created")