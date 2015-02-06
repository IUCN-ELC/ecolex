import sys
import os
import argparse
from utils import get_text_tika

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("Please install sqlalchemy and mysql-python for this script")
    sys.exit(0)


def get_full_text(files):
    return ''.join(get_text_tika(f) for f in files)


def update_dec(id_dec, full_text):
    conn.execute(
        text("UPDATE ai_decision SET text=:full_text WHERE `id`=:id_dec"),
        full_text=full_text, id_dec=id_dec,
    )


def get_path(path, basepath=None):
    basepath = basepath or ''
    file_path = os.path.abspath(os.path.join(basepath, path))
    if not os.path.exists(file_path):
        print("Error: {} does not exist".format(file_path))
        return None
    return file_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixsql", action='store_true')
    parser.add_argument("--basepath")
    parser.add_argument("database_uri")
    args = parser.parse_args()

    engine = create_engine(args.database_uri)
    conn = engine.connect()

    if args.fixsql:
        conn.execute("ALTER TABLE ai_decision ADD `text` TEXT")
        print("Alter ok")
    else:
        print("Fetching documents...")
        res = conn.execute("SELECT id_decision,path FROM ai_document")

        docs = {}
        for id_dec, path in res:
            docs.setdefault(id_dec, [])
            file_path = get_path(path, args.basepath)
            if file_path:
                docs[id_dec].append(file_path)

        for doc_id, files in docs.items():
            print("Processing doc: {}\n {}".format(doc_id, '\n '.join(files)))
            full_text = get_full_text(files)
            update_dec(doc_id, full_text)
