import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy.schema import CreateTable,CreateIndex
from sqlalchemy.dialects import mysql
from app.main import app
from app.models import Base

Path('docs').mkdir(exist_ok=True)
Path('database').mkdir(exist_ok=True)
Path('docs/openapi.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2),encoding='utf-8')
ddl=['-- MySQL 8.4 schema; UTF-8; generated from SQLAlchemy models.','CREATE DATABASE IF NOT EXISTS repair CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;','USE repair;']
for table in Base.metadata.sorted_tables:
    ddl.append(str(CreateTable(table).compile(dialect=mysql.dialect()))+';')
    for index in table.indexes:ddl.append(str(CreateIndex(index).compile(dialect=mysql.dialect()))+';')
Path('database/schema.mysql.sql').write_text('\n\n'.join(ddl),encoding='utf-8')
print('Exported docs/openapi.json and database/schema.mysql.sql')
